# -*- coding: utf-8 -*-
"""口播通顺性自查（2026-10-03 用户点名）：
把 12 条的「口播文案」+「提词器文案」两区原样导出到一个文件，供人眼逐条核。
不修改任何原稿。
"""
import glob
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

BASE = r"D:\个人资料\家庭教育\公众号\改善你的亲子关系\视频号文案"
OUT = os.path.join(BASE, "_过程文件", "_口播通顺自查_导出.txt")


def block(t, start_kw, end_kw):
    i = t.find(start_kw)
    if i < 0:
        return ""
    j = t.find(end_kw, i + len(start_kw))
    return t[i:j if j > 0 else len(t)]


def main():
    parts = []
    dirs = sorted(d for d in os.listdir(BASE)
                  if os.path.isdir(os.path.join(BASE, d)) and not d.startswith("_"))
    for d in dirs:
        fs = glob.glob(os.path.join(BASE, d, "视频号文案_*.md"))
        if not fs:
            continue
        t = io.open(fs[0], encoding="utf-8").read()
        oral = block(t, "## 一、口播文案", "\n## ")
        prompt = block(t, "## 二、提词器文案", "\n## ")
        parts.append("=" * 70)
        parts.append("### " + d)
        parts.append("--- 口播区 ---")
        parts.append(oral.strip())
        parts.append("")
        parts.append("--- 提词器区 ---")
        parts.append(prompt.strip())
        parts.append("")
    io.open(OUT, "w", encoding="utf-8").write("\n".join(parts))
    print("已导出：", OUT)
    print("条数：", len([p for p in parts if p.startswith("### ")]))
    print("字节：", os.path.getsize(OUT))


if __name__ == "__main__":
    main()
