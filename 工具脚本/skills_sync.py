#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
skills_sync.py —— 把「用户级技能」同步到本仓库的 `_技能/`（供 git 版本管理）

为什么要它
    技能的**源**在 `C:/Users/ZhuanZ/.workbuddy/skills/`，**不在本仓库**里——
    所以技能的改动默认进不了版本库、没法 diff、换机器就丢。
    本仓库保留一份**快照副本**在 `_技能/<技能名>/`，靠本脚本同步。

    ⭐ 还有第二类目标：**专家包要自包含**（如 family-education-learning-planner 把技能打进
    `skills/<技能名>/`）。这类副本同理由本脚本**单向镜像**——
    所以磁盘上虽然有多份，**真相源永远只有用户级那一份**，手改任何副本都会被下次同步覆盖。

用法
    python 工具脚本/skills_sync.py              # 同步（源 → 仓库快照 + 专家包镜像），列出变化
    python 工具脚本/skills_sync.py --check      # 只检查差异，不写入（推荐提交前跑）
    python 工具脚本/skills_sync.py --list       # 列出会同步的技能与其镜像目标
    python 工具脚本/skills_sync.py --src <目录> # 指定技能根目录（换机器用）
    python 工具脚本/skills_sync.py --local-only # 只同步 _技能/ 快照，跳过专家包镜像

    ⚠️ 删除保护：目标里多出来的文件默认**会被删除**（保持与源一致）。
       加 `--no-delete` 只增改、不删。

三条纪律
    1. ⛔ **不要直接改 `_技能/` 或专家包里的副本**——那是镜像，下次同步会被覆盖。
       要改就改「源」（`~/.workbuddy/skills/<技能名>/`），然后跑本脚本。
    2. 技能改动后**记得跑一次**（源和镜像不同步 = 仓库里是旧的、专家包是旧的）。
    3. 同步脚本本身也入库，换机器时改 `--src` 即可继续用。
"""
import argparse
import hashlib
import os
import shutil
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# 技能源目录（用户级）。可用 --src 覆盖；换机器时大概率要改这里。
DEFAULT_SRC = os.path.join(os.path.expanduser("~"), ".workbuddy", "skills")

# 仓库里的快照目录（相对本脚本上一级）
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DEST_ROOT = os.path.join(REPO, "_技能")

# 要同步的技能（按需增删）
SKILLS = [
    "ffmpeg-vertical-video-pipeline",
    "family-education-learning-coach",
]

# ⭐ 额外镜像目标：技能名 -> [「技能父目录」列表]
#    用户级技能会被完整镜像成 <目标>/<技能名>/，让专家包**自包含**。
#    新增带技能的专家包时，在这里加一行即可。
#    ⚠️ 老包有两条路径都要镜像（本仓库既有约定）：
#      ① `marketplaces/my-experts/plugins/<包>/skills` —— 建包/注册用的那棵，
#         也是重新打包 zip 的来源；
#      ② `cache/my-experts/<包>/<版本>/skills` —— 应用装载后运行的那棵。
#    ②**要等应用真正装载过该专家才会出现**（新建包此时还没有）；
#    目标父目录不存在时本脚本会**跳过**（不凭空创建），等它出现后自动开始镜像。
MIRROR_TARGETS = {
    "family-education-learning-coach": [
        "C:/Users/ZhuanZ/.workbuddy/plugins/marketplaces/my-experts/plugins/"
        "family-education-learning-planner/skills",
        "C:/Users/ZhuanZ/.workbuddy/plugins/cache/my-experts/"
        "family-education-learning-planner/1.0.0/skills",
    ],
}

# 忽略规则：目录名 / 文件名前缀 / 文件名后缀
SKIP_DIRS = {"__pycache__", ".git", ".idea", ".vscode"}
SKIP_FILE_PREFIX = ("_过程文件", "_备份", "_归档", "_tmp", ".", "~$")
SKIP_FILE_SUFFIX = (".pyc", ".pyo", ".tmp", ".bak", ".log", ".zip")


def md5(path, chunk=1 << 20):
    h = hashlib.md5()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def skip(name, is_dir):
    if is_dir:
        return name in SKIP_DIRS
    if name.startswith(SKIP_FILE_PREFIX):
        return True
    return name.lower().endswith(SKIP_FILE_SUFFIX)


def walk(root):
    """返回 {相对路径: 绝对路径}（已过滤）"""
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not skip(d, True)]
        for fn in filenames:
            if skip(fn, False):
                continue
            ap = os.path.join(dirpath, fn)
            out[os.path.relpath(ap, root).replace("\\", "/")] = ap
    return out


def sync_one(name, src_root, check_only=False, do_delete=True, dst=None, label="仓库快照"):
    src = os.path.join(src_root, name)
    if dst is None:
        dst = os.path.join(DEST_ROOT, name)
    if not os.path.isdir(src):
        print(f"  ⛔ 源不存在：{src}")
        return 1

    s_files = walk(src)
    d_files = walk(dst) if os.path.isdir(dst) else {}

    added = sorted(set(s_files) - set(d_files))
    removed = sorted(set(d_files) - set(s_files))
    changed = sorted(k for k in (set(s_files) & set(d_files))
                     if md5(s_files[k]) != md5(d_files[k]))

    print(f"  [{label}]")
    print(f"  源：{src}")
    print(f"  目标：{dst}")
    print(f"  新增 {len(added)} ／ 修改 {len(changed)} ／ 删除 {len(removed)}"
          f"（源共 {len(s_files)} 个文件）")
    for k in added:
        print(f"    + {k}")
    for k in changed:
        print(f"    ~ {k}")
    for k in removed:
        print(f"    - {k}")

    if check_only:
        return 0 if not (added or changed or removed) else 1

    if not (added or changed or removed):
        print("  ✅ 已是最新，无需同步")
        return 0

    # 复制
    for k in added + changed:
        target = os.path.join(dst, *k.split("/"))
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copy2(s_files[k], target)
    # 删除（源里已经没有的）
    if removed and do_delete:
        for k in removed:
            os.remove(os.path.join(dst, *k.split("/")))
        # 清掉空目录
        for dirpath, dirnames, filenames in os.walk(dst, topdown=False):
            if not dirnames and not filenames and dirpath != dst:
                os.rmdir(dirpath)
    elif removed:
        print("  ⚠️ --no-delete：目标里多余的文件未删除")

    print("  ✅ 同步完成")
    return 0


def main():
    ap = argparse.ArgumentParser(
        description="把用户级技能同步到仓库 _技能/ 快照 + 专家包镜像（供版本管理 / 专家包自包含）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("三条纪律")[0],
    )
    ap.add_argument("--src", default=DEFAULT_SRC, help=f"技能根目录（默认 {DEFAULT_SRC}）")
    ap.add_argument("--check", action="store_true", help="只检查差异，不写入")
    ap.add_argument("--no-delete", action="store_true", help="不删除目标里多余的文件")
    ap.add_argument("--list", action="store_true", help="列出会同步的技能与其镜像目标")
    ap.add_argument("--local-only", action="store_true", help="只同步 _技能/ 快照，跳过专家包镜像")
    args = ap.parse_args()

    src_root = os.path.abspath(args.src)
    if args.list:
        print(f"技能根目录：{src_root}")
        for n in SKILLS:
            ap_ = os.path.join(src_root, n)
            print(f"  {'✅' if os.path.isdir(ap_) else '❌'} {n}")
            print(f"       └─ 快照：{os.path.join(DEST_ROOT, n)}")
            for t in MIRROR_TARGETS.get(n, []):
                print(f"       └─ 镜像：{os.path.join(t, n)}")
        return 0

    print("=" * 64)
    print("技能同步（用户级源 → 仓库快照 + 专家包镜像）")
    print("=" * 64)
    rc = 0
    for n in SKILLS:
        rc |= sync_one(n, src_root, args.check, not args.no_delete)
        print()
        if args.local_only:
            continue
        for target_root in MIRROR_TARGETS.get(n, []):
            target_root = os.path.abspath(target_root)
            dst = os.path.join(target_root, n)
            if not os.path.isdir(target_root) and not os.path.isdir(dst):
                print(f"  [专家包镜像] ⏭ 目标父目录不存在，跳过（等它出现后自动镜像）：")
                print(f"      {target_root}")
                print()
                continue
            rc |= sync_one(n, src_root, args.check, not args.no_delete,
                           dst=dst, label="专家包镜像")
            print()
    if args.check and rc:
        print("⚠️ 有镜像落后于源 —— 跑一次不带 --check 的同步，再提交/打包。")
    return rc


if __name__ == "__main__":
    sys.exit(main())
