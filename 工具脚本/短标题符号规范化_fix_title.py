# -*- coding: utf-8 -*-
r"""
短标题符号规范化 —— 按**微信官方要求**把文案 MD 里的短标题候选改合规。

⛔ **微信官方原文**（2026-10-01 用户提供）：
   「标题包含特殊字符，符号**仅支持**书名号、引号、冒号、加号、问号、百分号、摄氏度，
     **逗号可用空格代替**」

→ 也就是说除了那七类，其余标点/符号**一律不支持**：顿号、感叹号、句号、括号、
  破折号、省略号、分号、竖线、斜杠、`@ # & *` 等都不行。
→ **逗号不是"删掉"，是"换成空格"**（直接删会让短语粘连：`查不出毛病不等于他在装`）。

本脚本只做两件事（**幂等**，重复跑不会变）：
  1. 把短标题候选里的 `，` 换成空格；
  2. 按新的标题重算 `（N 字）` 标注（口径 ＝ `video_script_check.visual_len`，不含空白）。

⛔ 不改任何其他行；跑完请用 `video_script_check.py` 复检。

用法：
  python 工具脚本/短标题符号规范化_fix_title.py <md 或目录> [--dry-run]
"""
from __future__ import annotations

import argparse
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# 行首编号 → 标题行（带「（N 字）」标注的写法）
CAND = re.compile(r"^(\s*(?:[①②③④⑤]|\d+[.、])\s*)(.*?)"
                  r"（\s*\d+\s*字[^）]*）(.*)$")
# 不带标注的写法（06 就是这样）：编号后直接是标题
BARE = re.compile(r"^(\s*(?:[①②③④⑤]|\d+[.、])\s*)(\S.*)$")


def visual_len(s: str) -> int:
    return len(re.sub(r"\s", "", s))


def zone_start(lines: list[str]):
    """定位「短标题」的标题行（判据同 video_script_check.py：不以 > 开头）"""
    for idx, ln in enumerate(lines):
        if ln.lstrip().startswith(">"):
            continue
        if "短标题" in ln and ("≤16" in ln or "16 字" in ln or "16字" in ln):
            return idx
    for idx, ln in enumerate(lines):
        if ln.lstrip().startswith(">"):
            continue
        if "视频号标题" in ln:
            return idx
    return None


def fix(text: str):
    lines = text.split("\n")
    st = zone_start(lines)
    if st is None:
        return text, []
    changes = []
    checked = 0
    for idx in range(st + 1, min(st + 13, len(lines))):
        ln = lines[idx]
        m = CAND.match(ln)
        ann = True
        if m:
            head, title, tail = m.groups()
        else:
            m2 = BARE.match(ln)
            if not m2:
                if checked:
                    break
                continue
            head, rest = m2.groups()
            title, sep, t2 = rest.partition("←")
            if sep:
                tail = "←" + t2
            else:
                tail = ""
            ann = False
            # 兜底护栏：不像标题的行（说明行、续行）不要动
            bare = title.replace("*", "").strip()
            if (not bare or visual_len(bare) > 40
                    or bare.startswith(("⚠️", "-", "*", ">"))):
                if checked:
                    break
                continue
        if not title.strip():
            continue
        checked += 1
        if "，" not in title:
            continue
        new_title = title.replace("，", " ")
        new_title = re.sub(r"[ \t]{2,}", " ", new_title)
        n = visual_len(new_title.replace("*", ""))
        lines[idx] = f"{head}{new_title}（{n} 字）{tail}"
        changes.append((title.replace("*", ""), new_title.replace("*", ""), n,
                        "" if ann else "（原本没有字数标注，顺带补上）"))
    return "\n".join(lines), changes


def main() -> int:
    ap = argparse.ArgumentParser(description="短标题符号规范化（微信官方口径）")
    ap.add_argument("target")
    ap.add_argument("--dry-run", action="store_true", dest="dry")
    a = ap.parse_args()

    files = []
    if os.path.isdir(a.target):
        for root, dirs, fs in os.walk(a.target):
            dirs[:] = [d for d in dirs if d != "_过程文件"]
            files += [os.path.join(root, f) for f in sorted(fs)
                      if f.endswith(".md") and not f.startswith("_")]
    else:
        files = [a.target]

    total = 0
    for p in files:
        raw = open(p, encoding="utf-8").read()
        new, changes = fix(raw)
        if not changes:
            continue
        total += len(changes)
        print(f"\n{os.path.basename(p)}")
        for old, nw, n, note in changes:
            print(f"  旧：{old}")
            print(f"  新：{nw}   （{n} 字）{note}")
        if not a.dry:
            with open(p, "w", encoding="utf-8", newline="") as fh:
                fh.write(new)
    print(f"\n{'（--dry-run，未写入）' if a.dry else '已写入'}"
          f"：{total} 个短标题候选被规范化")
    return 0


if __name__ == "__main__":
    sys.exit(main())
