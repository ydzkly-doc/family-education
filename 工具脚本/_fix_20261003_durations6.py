# -*- coding: utf-8 -*-
'''12 条抬头块时长回填（系列重做后，2026-10-03）。数字全部取自 video_series_batch 实测。'''
import glob
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
BASE = r"D:\个人资料\家庭教育\公众号\改善你的亲子关系\视频号文案"

D = {
    "01": (164, "2:44.4", 707, "173~176", "2.9"),
    "02": (126, "2:05.6", 540, "132~134", "2.2"),
    "03": (153, "2:33.0", 658, "161~164", "2.7"),
    "04": (154, "2:34.4", 664, "162~165", "2.8"),
    "05": (149, "2:29.1", 641, "157~160", "2.7"),
    "06": (139, "2:19.1", 598, "146~149", "2.5"),
    "07": (128, "2:07.9", 550, "134~137", "2.3"),
    "08": (168, "2:47.9", 722, "176~180", "3.0"),
    "09": (167, "2:46.7", 717, "175~178", "3.0"),
    "10": (136, "2:15.8", 584, "143~145", "2.4"),
    "11": (124, "2:04.4", 535, "131~133", "2.2"),
    "12": (131, "2:10.9", 563, "137~140", "2.3"),
}
PAT = re.compile(r"\*\*时长 ≈\d+ 秒（[^）]+）／口播 \d+ 字含标点；真片预计 \d+~\d+ 秒（[^）]+）")

bad = 0
for pre, (sec, mmss, words, span, grade) in D.items():
    d = glob.glob(os.path.join(BASE, pre + "_*"))
    if not d:
        print("❌ 找不到", pre); bad += 1; continue
    p = glob.glob(os.path.join(d[0], "视频号文案_*.md"))[0]
    t = io.open(p, encoding="utf-8").read()
    new = "**时长 ≈%d 秒（%s）／口播 %d 字含标点；真片预计 %s 秒（%s 分）" % (sec, mmss, words, span, grade)
    t2, n = PAT.subn(new, t, count=1)
    if n != 1:
        print("❌ %s 未命中抬头块" % pre); bad += 1; continue
    io.open(p, "w", encoding="utf-8").write(t2)
    print("✅ %s → %d 秒 / %d 字 / %s 秒" % (pre, sec, words, span))
print("完成，异常 %d" % bad)
