# -*- coding: utf-8 -*-
'''抬头块时长回填 第五轮（人话化改稿后，12 条全部重算）。
数字取自 video_series_batch.py 实测输出，不手写估算。
'''
import glob
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

BASE = r"D:\个人资料\家庭教育\公众号\改善你的亲子关系\视频号文案"

D = {
    "01": (165, "2:44.9", 709, "173~176", "2.9"),
    "02": (129, "2:08.8", 554, "135~138", "2.3"),
    "03": (127, "2:07.0", 546, "133~136", "2.3"),
    "04": (154, "2:34.0", 662, "162~165", "2.7"),
    "05": (144, "2:24.4", 621, "152~155", "2.6"),
    "06": (136, "2:15.6", 583, "142~145", "2.4"),
    "07": (127, "2:07.2", 547, "134~136", "2.3"),
    "08": (168, "2:48.4", 724, "177~180", "3.0"),
    "09": (167, "2:46.5", 716, "175~178", "3.0"),
    "10": (136, "2:16.3", 586, "143~146", "2.4"),
    "11": (124, "2:03.7", 532, "130~132", "2.2"),
    "12": (130, "2:09.8", 558, "136~139", "2.3"),
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
