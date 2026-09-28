# -*- coding: utf-8 -*-
r"""核对各条文案 MD 里「视频描述」的字数（视频号：官方上限 1000 字，本项目自定 ≤100 字）。

为什么要脚本：**手算一定会错**（项目里已踩过"字数沿用旧数字"的坑）。
判据：脚本报 OK 才算过。

用法：
    PY="C:/Users/ZhuanZ/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
    "$PY" 工具脚本/check_desc_len.py                 # 扫本系列六条（存在几条扫几条）
    "$PY" 工具脚本/check_desc_len.py <md 路径> ...    # 指定文件
    SHOW=1 "$PY" 工具脚本/check_desc_len.py          # 顺便把描述原文打出来

背景（2026-09-26）：
    视频号发布页**没有"标题"字段**——只有「描述」（上限 1000 字）；
    描述**超过 16 字**才会出现「短标题」输入框（≤16 字，会展示在搜索/话题/地点/订阅号消息）。
    本项目把描述控制在 **≤100 字**：手机端只显示前 2~3 行，且另有非官方资料称长视频限 100 字。
"""
from __future__ import annotations

import io
import os
import re
import sys

SERIES = (r"D:/个人资料/家庭教育/孩子不上学了怎么办/视频号文案")
LIMIT = 100

# 六条（发布序）；缺目录就跳过
DIRS = ["01_别再说装病", "02_第一句话问错了", "03_别问这是谁的错",
        "04_四步对话", "05_各拉各的车", "06_报班治的是我的慌"]

PAT = re.compile(r"\*\*⭐+ 视频描述[^\n]*\*\*[^\n]*\n\s*```\s*\n(.*?)\n\s*```", re.S)


def find_md(dirname: str) -> str | None:
    d = os.path.join(SERIES, dirname)
    if not os.path.isdir(d):
        return None
    for f in sorted(os.listdir(d)):
        if f.endswith(".md"):
            return os.path.join(d, f)
    return None


def main() -> int:
    args = sys.argv[1:]
    paths = args or [p for p in (find_md(x) for x in DIRS) if p]
    if not paths:
        print("!! 没找到任何 md")
        return 1

    bad = 0
    for p in paths:
        name = os.path.basename(os.path.dirname(p))
        t = io.open(p, encoding="utf-8").read()
        m = PAT.search(t)
        if not m:
            print(f"  {name}: 未找到「视频描述」区块  ← 需要补")
            bad += 1
            continue
        desc = m.group(1).strip()
        n = len(desc)
        ok = n <= LIMIT
        if not ok:
            bad += 1
        print(f"  {name}: {n} 字  {'OK' if ok else f'超 {LIMIT}!'}")
        if os.environ.get("SHOW"):
            print("     " + desc)

    print(f"\n{'✅ 全部达标（≤%d 字）' % LIMIT if not bad else '⚠️ %d 处需要处理' % bad}")
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
