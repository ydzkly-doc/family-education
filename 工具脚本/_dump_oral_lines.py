# -*- coding: utf-8 -*-
'''导出 12 条「口播文案」原文（口径：只出口播区，逐行编号，方便逐句按"听"来判）。
'''
import glob
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

BASE = r"D:\个人资料\家庭教育\公众号\改善你的亲子关系\视频号文案"
OUT = os.path.join(BASE, "_过程文件", "_口播通读稿.txt")


def main():
    parts = []
    dirs = sorted(d for d in os.listdir(BASE)
                  if os.path.isdir(os.path.join(BASE, d)) and not d.startswith("_"))
    for d in dirs:
        f = glob.glob(os.path.join(BASE, d, "视频号文案_*.md"))
        if not f:
            continue
        t = io.open(f[0], encoding="utf-8").read()
        oral = t.split("## 一、口播文案", 1)[1].split("\n## ", 1)[0]
        parts.append("=" * 64)
        parts.append("### " + d)
        n = 0
        for ln in oral.split("\n"):
            s = ln.strip()
            if not s:
                continue
            if s.startswith("【"):
                parts.append("")
                parts.append(s)
                n = 0
                continue
            n += 1
            parts.append(f"  {n:02d} {s}")
        parts.append("")
    io.open(OUT, "w", encoding="utf-8").write("\n".join(parts))
    print("已导出：", OUT)


if __name__ == "__main__":
    main()
