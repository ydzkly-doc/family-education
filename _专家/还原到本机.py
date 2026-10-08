#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""还原到本机.py —— 换新电脑时，把 git 里的专家包快照写回本机。

什么时候用
    换了电脑（或重装了系统）：先装好 WorkBuddy、clone 本仓库，然后跑本脚本。
    它把仓库 `_专家/plugins/<包>/` 的完整快照，写回本机两处：
      · marketplaces/my-experts/plugins/<包>/   —— 注册/建包那棵
      · cache/my-experts/<包>/<版本>/           —— 运行时装载那棵
        （版本号取自该包 plugin.json 的 version；读不到就用 --version 指定，默认 1.0.0）
    写完**重启 WorkBuddy**，专家即出现。

用法（Git Bash）
    PY="C:/Users/ZhuanZ/.workbuddy/binaries/python/versions/3.13.12/python.exe"
    "$PY" _专家/还原到本机.py --check      # 只看会改什么，不写入（第一次先跑这个）
    "$PY" _专家/还原到本机.py              # 执行还原
    "$PY" _专家/还原到本机.py video-script-studio   # 只还原一个包
    "$PY" _专家/还原到本机.py --version 1.0.2       # 手动指定 cache 版本目录

注意
    · 本脚本会把快照**完整覆盖**到目标（先清空目标再拷贝），保证与 git 一致；
      目标里若有未提交的本地改动会被覆盖 —— 先用 --check 看清楚。
    · family-education-learning-planner 只写 marketplace（它从不进 cache）。
"""
import argparse
import json
import os
import shutil
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HOME = os.path.expanduser("~")
CACHE_ROOT = os.path.join(HOME, ".workbuddy", "plugins", "cache", "my-experts")
MKT_ROOT = os.path.join(HOME, ".workbuddy", "plugins", "marketplaces",
                        "my-experts", "plugins")

HERE = os.path.dirname(os.path.abspath(__file__))
SNAP_ROOT = os.path.join(HERE, "plugins")

# 只写 marketplace、不写 cache 的包
MARKETPLACE_ONLY = {"family-education-learning-planner"}

SKIP_DIRS = {".in_use", ".git", "__pycache__", ".pytest_cache", ".idea", ".vscode"}


def read_version(snap_dir, fallback="1.0.0"):
    """从 .codebuddy-plugin/plugin.json 读 version，读不到用 fallback。"""
    pj = os.path.join(snap_dir, ".codebuddy-plugin", "plugin.json")
    try:
        with open(pj, "r", encoding="utf-8") as f:
            data = json.load(f)
        v = str(data.get("version") or "").strip()
        if v:
            return v
    except Exception:
        pass
    return fallback


def copy_tree_clean(src, dst, check_only):
    """先清空 dst 再整体拷贝 src（保证完全一致）。"""
    exists = os.path.isdir(dst)
    if check_only:
        print(f"      → 将覆盖到：{dst}" + ("（目标已存在）" if exists else "（新建）"))
        return
    if exists:
        shutil.rmtree(dst)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns(*SKIP_DIRS))
    print(f"      ✓ 已写入：{dst}")


def restore(pkg, check_only, version_override):
    snap = os.path.join(SNAP_ROOT, pkg)
    if not os.path.isdir(snap):
        print(f"  ⛔ 快照不存在：{snap}")
        return False
    ver = version_override or read_version(snap)
    print(f"\n[{pkg}]  快照：{snap}")

    # ① marketplace
    copy_tree_clean(snap, os.path.join(MKT_ROOT, pkg), check_only)

    # ② cache（planner 等跳过）
    if pkg in MARKETPLACE_ONLY:
        print("      · 该包只写 marketplace（不进 cache）")
    else:
        copy_tree_clean(snap, os.path.join(CACHE_ROOT, pkg, ver), check_only)
    return True


def main():
    ap = argparse.ArgumentParser(description="把 git 专家包快照还原到本机")
    ap.add_argument("packages", nargs="*", help="包名（省略＝全部）")
    ap.add_argument("--check", action="store_true", help="只看差异，不写入")
    ap.add_argument("--version", default=None, help="手动指定 cache 版本目录")
    a = ap.parse_args()

    if not os.path.isdir(SNAP_ROOT):
        print(f"⛔ 找不到快照目录：{SNAP_ROOT}")
        return 1
    pkgs = a.packages or sorted(
        d for d in os.listdir(SNAP_ROOT)
        if os.path.isdir(os.path.join(SNAP_ROOT, d)))

    print("=" * 64)
    print("还原专家包到本机" + "（只检查，不写入）" if a.check else "还原专家包到本机")
    print(f"  快照来源：{SNAP_ROOT}")
    print(f"  marketplace：{MKT_ROOT}")
    print(f"  cache：{CACHE_ROOT}")
    print("=" * 64)

    results = {p: restore(p, a.check, a.version) for p in pkgs}
    bad = [p for p, ok in results.items() if not ok]
    print("\n" + "=" * 64)
    if bad:
        print(f"❌ {len(bad)} 个包失败：{', '.join(bad)}")
        return 1
    print("✅ 全部完成。请重启 WorkBuddy 让专家生效。")
    print("   （--check 模式下没有实际写入）" if a.check else "")
    return 0


if __name__ == "__main__":
    sys.exit(main())
