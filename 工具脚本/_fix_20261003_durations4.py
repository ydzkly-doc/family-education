# -*- coding: utf-8 -*-
'''抬头块时长回填 第四轮（3.9 对齐改稿后）。数字取自 video_series_batch.py 实测输出。
只回填有变化的 4 条（03 ／ 04 ／ 05 ／ 07）。
'''
import glob
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

BASE = r"D:\个人资料\家庭教育\公众号\改善你的亲子关系\视频号文案"

D = {
    "03": (125, "2:05.3", 539, "132~134", "2.2"),
    "04": (155, "2:35.3", 668, "163~166", "2.8"),
    "05": (146, "2:25.6", 626, "153~156", "2.6"),
    "07": (129, "2:08.8", 554, "135~138", "2.3"),
}

PAT = re.compile(
    r"\*\*时长 ≈\d+ 秒（[^）]+）／口播 \d+ 字含标点；真片预计 \d+~\d+ 秒（[^）]+）"
)


def main():
    bad = 0
    for pre, (sec, mmss, words, span, grade) in D.items():
        d = glob.glob(os.path.join(BASE, pre + "_*"))
        if not d:
            print(f"❌ 找不到 {pre}")
            bad += 1
            continue
        p = glob.glob(os.path.join(d[0], "视频号文案_*.md"))[0]
        t = io.open(p, encoding="utf-8").read()
        new = (f"**时长 ≈{sec} 秒（{mmss}）／口播 {words} 字含标点；"
               f"真片预计 {span} 秒（{grade} 分）")
        t2, n = PAT.subn(new, t, count=1)
        if n != 1:
            print(f"❌ {pre} 未命中抬头块")
            bad += 1
            continue
        io.open(p, "w", encoding="utf-8").write(t2)
        print(f"✅ {pre} → {sec} 秒 / {words} 字 / 真片 {span} 秒")
    print(f"\n完成，异常 {bad} 处")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
