# -*- coding: utf-8 -*-
'''抬头块时长回填 第三轮（2026-10-03 口播通顺性修正后）。
数字全部取自 video_series_batch.py 的实测输出，不手写估算。
'''
import glob
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

BASE = r"D:\个人资料\家庭教育\公众号\改善你的亲子关系\视频号文案"

# 条目录前缀 -> (时长秒, 分:秒, 口播字数, 真片区间, 分档)
D = {
    "01": (166, "2:45.6", 712, "174~177", "3.0"),
    "02": (129, "2:08.8", 554, "135~138", "2.3"),
    "03": (126, "2:05.6", 540, "132~134", "2.2"),
    "04": (155, "2:35.1", 667, "163~166", "2.8"),
    "05": (145, "2:25.1", 624, "152~155", "2.6"),
    "06": (135, "2:15.3", 582, "142~145", "2.4"),
    "07": (128, "2:08.4", 552, "135~137", "2.3"),
    "08": (171, "2:50.7", 734, "179~183", "3.0"),
    "09": (165, "2:44.9", 709, "173~176", "2.9"),
    "10": (136, "2:16.0", 585, "143~146", "2.4"),
    "11": (123, "2:02.8", 528, "129~131", "2.2"),
    "12": (130, "2:09.5", 557, "136~139", "2.3"),
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
        fs = glob.glob(os.path.join(d[0], "视频号文案_*.md"))
        p = fs[0]
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
