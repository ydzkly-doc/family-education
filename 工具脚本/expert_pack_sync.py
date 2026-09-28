#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""专家包同步：cache → marketplace → zip → 归一化比对（一条命令跑完）。

为什么要有它（2026-09-27 立）：
    改 SOP 是**常态动作**（每轮反馈都可能改），而"改完要同步三处"的顺序固定、
    手工做**每次都要重写一遍临时脚本**，还踩过坑：
      ⚠️ `.in_use/`（运行时标记目录）会被一起打进 zip → 与 marketplace 比对**必 FAIL**。
    所以固化成本脚本：**排除运行时目录** + **三方 md5 逐文件比对**。

用法：
    PY="C:/Users/ZhuanZ/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
    "$PY" 工具脚本/expert_pack_sync.py                      # 同步全部 my-experts 包
    "$PY" 工具脚本/expert_pack_sync.py video-script-studio  # 只同步一个包
    "$PY" 工具脚本/expert_pack_sync.py --check              # 只比对，不写入

固定顺序（⛔ 别调换）：
    ① 改 `cache/my-experts/<包>/<版本>/`（**唯一真相源**）
    ② 复制到 `marketplaces/my-experts/plugins/<包>/`
    ③ 重打包 `_专家/<包>.zip`（**顶层目录 = 包名**，不是版本号）
    ④ 三方逐文件 md5 比对 → PASS 才交付

⚠️ 专家包**不热加载**：改完下个会话才生效。
⚠️ 多版本时取**版本号最大**的那个目录（1.0.0 < 1.0.1 < 2.0.0）。
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
ZIP_DIR = r"D:\个人资料\家庭教育\_专家"

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
    """→ [(相对路径(正斜杠), 绝对路径)]，跳过运行时目录"""
    out = []
    for root, dirs, files in os.walk(base):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for f in sorted(files):
            full = os.path.join(root, f)
            rel = os.path.relpath(full, base).replace("\\", "/")
            out.append((rel, full))
    return out


def scan(base: str):
    return {rel: md5(io.open(full, "rb").read()) for rel, full in walk_files(base)}


def sync_one(pkg: str, check_only: bool = False) -> bool:
    pkg_cache_root = os.path.join(CACHE_ROOT, pkg)
    if not os.path.isdir(pkg_cache_root):
        print(f"  ⚠️ 跳过：cache 里没有这个包（{pkg_cache_root}）")
        return False
    ver = latest_version(pkg_cache_root)
    if not ver:
        print(f"  ⚠️ 跳过：cache/{pkg} 下没有版本目录")
        return False
    src = os.path.join(pkg_cache_root, ver)
    dst = os.path.join(MKT_ROOT, pkg)
    zip_path = os.path.join(ZIP_DIR, f"{pkg}.zip")

    print(f"\n{'=' * 66}\n[{pkg}]  版本 {ver}")
    if not os.path.isdir(dst):
        print(f"  ⚠️ marketplace 里没有这个包（{dst}）→ 跳过（需要先建目录）")
        return False

    # ② 同步 marketplace
    if not check_only:
        for rel, full in walk_files(src):
            target = os.path.join(dst, rel.replace("/", os.sep))
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.copy2(full, target)
        # 删掉 marketplace 里多出来的文件（源已删的）
        src_rels = {rel for rel, _ in walk_files(src)}
        for rel, full in walk_files(dst):
            if rel not in src_rels:
                os.remove(full)
                print(f"  - 已删除多余文件：{rel}")
        print(f"  ✓ marketplace 已同步（{len(src_rels)} 个文件）")

    # ③ 重打包 zip
    if not check_only:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            for rel, full in walk_files(src):
                z.write(full, f"{pkg}/{rel}")
        print(f"  ✓ 已重打包 → {zip_path}")
    elif not os.path.exists(zip_path):
        print(f"  ⚠️ zip 不存在：{zip_path}")
        return False

    # ④ 三方比对
    a, b = scan(src), scan(dst)
    with zipfile.ZipFile(zip_path) as z:
        c = {n[len(pkg) + 1:]: md5(z.read(n))
             for n in z.namelist() if not n.endswith("/")}
    ok = True
    for name in sorted(set(a) | set(b) | set(c)):
        va, vb, vc = a.get(name), b.get(name), c.get(name)
        same = va == vb == vc
        ok &= same
        if not same or not check_only:
            print(f"    {'✅' if same else '❌'} {name}"
                  f"  cache={str(va)[:8]} marketplace={str(vb)[:8]} zip={str(vc)[:8]}")
    print("  " + ("✅ PASS —— cache / marketplace / zip 三方一致"
                  if ok else "❌ FAIL —— 三方不一致，先别交付"))
    return ok


def main():
    ap = argparse.ArgumentParser(description="专家包同步（cache→marketplace→zip→比对）")
    ap.add_argument("packages", nargs="*", help="包名（省略＝全部）")
    ap.add_argument("--check", action="store_true", help="只比对，不写入")
    a = ap.parse_args()

    pkgs = a.packages or sorted(
        d for d in os.listdir(CACHE_ROOT)
        if os.path.isdir(os.path.join(CACHE_ROOT, d)))
    print("专家包同步" + ("（只比对）" if a.check else ""))
    print(f"  cache：{CACHE_ROOT}")
    print(f"  marketplace：{MKT_ROOT}")
    print(f"  zip 输出：{ZIP_DIR}")

    results = {p: sync_one(p, a.check) for p in pkgs}
    print("\n" + "=" * 66)
    bad = [p for p, ok in results.items() if not ok]
    for p, ok in results.items():
        print(f"  {'✅' if ok else '❌'} {p}")
    if bad:
        print(f"\n❌ {len(bad)} 个包未通过：{', '.join(bad)}")
        return 1
    print("\n✅ 全部通过（⚠️ 专家包不热加载，下个会话生效）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
