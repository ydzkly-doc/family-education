#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""专家包同步：真相源 → marketplace → 仓库快照(_专家/plugins) → zip → 归一化比对。

为什么要有它（2026-09-27 立；2026-10-08 改版）：
    改 SOP 是**常态动作**（每轮反馈都可能改），而"改完要同步多处"的顺序固定、
    手工做**每次都要重写一遍临时脚本**，还踩过坑：
      ⚠️ `.in_use/`（运行时标记目录）会被一起打进 zip → 比对**必 FAIL**。
    所以固化成本脚本：**排除运行时目录** + **多目标 md5 逐文件比对**。

⭐ 2026-10-08 改版：专家包纳入 git，便于换电脑恢复。
    · 仓库内放**解压后的完整快照** `_专家/plugins/<包>/`（可逐文件 diff/review）；
    · zip 退化为**本地构建产物**（默认不再进 git，见 .gitignore）；
    · 换新电脑用 `_专家/还原到本机.py` 把快照写回本机 marketplace / cache。

用法：
    PY="C:/Users/ZhuanZ/.workbuddy/binaries/python/versions/3.13.12/python.exe"
    "$PY" 工具脚本/expert_pack_sync.py                      # 同步全部 my-experts 包
    "$PY" 工具脚本/expert_pack_sync.py video-script-studio  # 只同步一个包
    "$PY" 工具脚本/expert_pack_sync.py --check              # 只比对，不写入
    "$PY" 工具脚本/expert_pack_sync.py --no-zip             # 不重打包 zip
    "$PY" 工具脚本/expert_pack_sync.py --snapshot-only      # 只刷仓库快照(不碰 marketplace/zip)

固定顺序（⛔ 别调换）：
    ① 改**真相源**：
         · 普通包 = `cache/my-experts/<包>/<版本>/`（唯一真相源，多版本取号最大）
         · planner（family-education-learning-planner）= marketplace 那份
           （它从未装进 cache；见 SOURCE_IS_MARKETPLACE）
    ② 复制到 `marketplaces/my-experts/plugins/<包>/`（planner 本身就在此，跳过）
    ③ 镜像到仓库快照 `_专家/plugins/<包>/`（**这一份进 git**）
    ④ 重打包 `_专家/<包>.zip`（本地产物，顶层目录 = 包名）
    ⑤ 多目标逐文件 md5 比对 → PASS 才交付

⚠️ 专家包**不热加载**：改完下个会话才生效。
"""
import argparse
import hashlib
import io
import os
import re
import shutil
import sys
import zipfile

HOME = os.path.expanduser("~")
CACHE_ROOT = os.path.join(HOME, ".workbuddy", "plugins", "cache", "my-experts")
MKT_ROOT = os.path.join(HOME, ".workbuddy", "plugins", "marketplaces",
                        "my-experts", "plugins")

# 仓库根目录（本脚本在 <仓库>/工具脚本/ 下）
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
ZIP_DIR = os.path.join(REPO, "_专家")
SNAP_ROOT = os.path.join(REPO, "_专家", "plugins")

# ⛔ 真相源不在 cache、而在 marketplace 的包（从未装进 cache）。
#    这类包：源 = marketplace/<包>/，同步时跳过「cache→marketplace」那一步。
SOURCE_IS_MARKETPLACE = {"family-education-learning-planner"}

# ⚠️ 运行时/仓库痕迹**不进包**
SKIP_DIRS = {".in_use", ".git", "__pycache__", ".pytest_cache", ".idea", ".vscode"}


def md5(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()


def latest_version(pkg_dir: str):
    """cache 里取版本号最大的子目录"""
    vers = [d for d in os.listdir(pkg_dir)
            if os.path.isdir(os.path.join(pkg_dir, d)) and re.match(r"^\d+(\.\d+)*$", d)]
    if not vers:
        return None
    return max(vers, key=lambda v: [int(x) for x in v.split(".")])


def walk_files(base: str):
    """→ [(相对路径(正斜杠), 绝对路径)]，跳过运行时目录。base 不存在→空。"""
    out = []
    if not os.path.isdir(base):
        return out
    for root, dirs, files in os.walk(base):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for f in sorted(files):
            full = os.path.join(root, f)
            rel = os.path.relpath(full, base).replace("\\", "/")
            out.append((rel, full))
    return out


def scan(base: str):
    return {rel: md5(io.open(full, "rb").read()) for rel, full in walk_files(base)}


def mirror(src: str, dst: str, check_only: bool, label: str):
    """把 src 完整镜像到 dst（含删除多余文件）。返回源文件 rel 集合。"""
    src_items = walk_files(src)
    src_rels = {rel for rel, _ in src_items}
    if check_only:
        return src_rels
    os.makedirs(dst, exist_ok=True)
    for rel, full in src_items:
        target = os.path.join(dst, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copy2(full, target)
    for rel, full in walk_files(dst):
        if rel not in src_rels:
            os.remove(full)
            print(f"  - [{label}] 删除多余文件：{rel}")
    # 清掉残留空目录
    for root, dirs, files in os.walk(dst, topdown=False):
        if root == dst:
            continue
        if not os.listdir(root):
            os.rmdir(root)
    print(f"  ✓ {label} 已镜像（{len(src_rels)} 个文件）→ {dst}")
    return src_rels


def resolve_source(pkg: str):
    """返回 (真相源绝对路径, 版本号或None, 是否源在marketplace)。找不到→(None,...)"""
    if pkg in SOURCE_IS_MARKETPLACE:
        src = os.path.join(MKT_ROOT, pkg)
        if os.path.isdir(src):
            return src, None, True
        return None, None, True
    pkg_cache_root = os.path.join(CACHE_ROOT, pkg)
    if not os.path.isdir(pkg_cache_root):
        return None, None, False
    ver = latest_version(pkg_cache_root)
    if not ver:
        return None, None, False
    return os.path.join(pkg_cache_root, ver), ver, False


def sync_one(pkg: str, check_only=False, do_zip=True, snapshot_only=False) -> bool:
    src, ver, src_in_mkt = resolve_source(pkg)
    if not src:
        where = "marketplace" if src_in_mkt else "cache"
        print(f"  ⚠️ 跳过：{where} 里找不到这个包（{pkg}）")
        return False

    dst_mkt = os.path.join(MKT_ROOT, pkg)
    snap = os.path.join(SNAP_ROOT, pkg)
    zip_path = os.path.join(ZIP_DIR, f"{pkg}.zip")

    ver_txt = f"（源在 marketplace）" if src_in_mkt else f"版本 {ver}"
    print(f"\n{'=' * 66}\n[{pkg}]  {ver_txt}\n  源：{src}")

    if not snapshot_only:
        # ② 源 → marketplace（源就在 marketplace 的包跳过）
        if src_in_mkt:
            if not os.path.isdir(dst_mkt):
                print(f"  ⚠️ marketplace 目录不存在：{dst_mkt}")
                return False
            print("  · 源即 marketplace，跳过 ②")
        else:
            if not os.path.isdir(dst_mkt):
                print(f"  ⚠️ marketplace 里没有这个包（{dst_mkt}）→ 跳过（需先建目录）")
                return False
            mirror(src, dst_mkt, check_only, "marketplace")

    # ③ 源 → 仓库快照（始终做；这一份进 git）
    mirror(src, snap, check_only, "仓库快照")

    # ④ 重打包 zip（本地构建产物）
    if do_zip and not snapshot_only:
        if not check_only:
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
                for rel, full in walk_files(src):
                    z.write(full, f"{pkg}/{rel}")
            print(f"  ✓ 已重打包 → {zip_path}")
        elif not os.path.exists(zip_path):
            print(f"  ⚠️ zip 不存在：{zip_path}")

    # ⑤ 多目标比对：源 / marketplace / 仓库快照 / zip
    a = scan(src)
    targets = {"源": a}
    if not snapshot_only and (src_in_mkt or os.path.isdir(dst_mkt)):
        targets["marketplace" if not src_in_mkt else "marketplace(源)"] = scan(dst_mkt)
    targets["仓库快照"] = scan(snap)
    if do_zip and not snapshot_only and os.path.exists(zip_path):
        with zipfile.ZipFile(zip_path) as z:
            targets["zip"] = {n[len(pkg) + 1:]: md5(z.read(n))
                              for n in z.namelist() if not n.endswith("/")}

    all_names = set()
    for m in targets.values():
        all_names |= set(m)
    ok = True
    for name in sorted(all_names):
        vals = {label: m.get(name) for label, m in targets.items()}
        same = len(set(vals.values())) == 1
        ok &= same
        if not same or not check_only:
            tag = "✅" if same else "❌"
            digests = " ".join(f"{label}={str(v)[:8]}" for label, v in vals.items())
            print(f"    {tag} {name}  {digests}")
    labels = " / ".join(targets.keys())
    print("  " + (f"✅ PASS —— {labels} 全部一致"
                  if ok else f"❌ FAIL —— {labels} 不一致，先别交付"))
    return ok


def discover_packages():
    """要同步的包：cache 里的 + 源在 marketplace 的，去重排序。"""
    pkgs = set(SOURCE_IS_MARKETPLACE)
    if os.path.isdir(CACHE_ROOT):
        for d in os.listdir(CACHE_ROOT):
            if os.path.isdir(os.path.join(CACHE_ROOT, d)):
                pkgs.add(d)
    return sorted(pkgs)


def main():
    ap = argparse.ArgumentParser(description="专家包同步（源→marketplace→仓库快照→zip→比对）")
    ap.add_argument("packages", nargs="*", help="包名（省略＝全部）")
    ap.add_argument("--check", action="store_true", help="只比对，不写入")
    ap.add_argument("--no-zip", action="store_true", help="不重打包 zip")
    ap.add_argument("--snapshot-only", action="store_true",
                    help="只把源刷进仓库快照，不碰 marketplace/zip")
    a = ap.parse_args()

    pkgs = a.packages or discover_packages()
    print("专家包同步" + ("（只比对）" if a.check else ""))
    print(f"  cache：{CACHE_ROOT}")
    print(f"  marketplace：{MKT_ROOT}")
    print(f"  仓库快照：{SNAP_ROOT}（进 git）")
    print(f"  zip 输出：{os.path.join(ZIP_DIR, '<包>.zip')}（本地产物）")

    results = {p: sync_one(p, a.check, not a.no_zip, a.snapshot_only)
               for p in pkgs}
    print("\n" + "=" * 66)
    for p, ok in results.items():
        print(f"  {'✅' if ok else '❌'} {p}")
    bad = [p for p, ok in results.items() if not ok]
    if bad:
        print(f"\n❌ {len(bad)} 个包未通过：{', '.join(bad)}")
        return 1
    print("\n✅ 全部通过（⚠️ 专家包不热加载，下个会话生效）")
    print("   提交前：git add _专家/plugins 后再 commit/push")
    return 0


if __name__ == "__main__":
    sys.exit(main())
