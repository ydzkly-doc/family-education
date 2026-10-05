# -*- coding: utf-8 -*-
'''扫描 12 条里 ASCII 单引号 / 中文引号 的使用（口播稿引号风格应统一为 ASCII 双引号）。
'''
import glob
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

BASE = r"D:\个人资料\家庭教育\公众号\改善你的亲子关系\视频号文案"


def main():
    tot = 0
    for d in sorted(os.listdir(BASE)):
        p = os.path.join(BASE, d)
        if not os.path.isdir(p) or d.startswith("_"):
            continue
        for f in glob.glob(os.path.join(p, "视频号文案_*.md")):
            t = io.open(f, encoding="utf-8").read()
            for i, ln in enumerate(t.split("\n"), 1):
                if "'" in ln or "\u201c" in ln or "\u201d" in ln:
                    tot += 1
                    print(f"{d[:14]} L{i}: {ln.strip()[:110]}")
    print(f"\n共 {tot} 行含 ASCII 单引号或中文引号")


if __name__ == "__main__":
    main()
