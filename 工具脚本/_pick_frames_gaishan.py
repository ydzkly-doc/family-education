# -*- coding: utf-8 -*-
"""《改善你的亲子关系》12 条：从各条「无封面卡」成片抽候选帧，供目挑封面底图。
每条在 30%/55%/75% 处各抽一帧（避开开头 0~2s 封面卡与结尾留白）。
底片来源＝_成品/_旧版本/成片_NN_无封面卡.mp4（正片，时间点直接对应）。
"""
import os
import subprocess

FFMPEG = r"C:\Users\ZhuanZ\.workbuddy\binaries\ffmpeg\bin\ffmpeg.exe"
BASE = r"D:\个人资料\家庭教育\公众号\改善你的亲子关系\视频号文案"
OUT = r"D:\个人资料\家庭教育\_过程文件\帧候选\改善"
os.makedirs(OUT, exist_ok=True)

# (编号, 目录名, 无卡版时长秒)
CLIPS = [
    ("01", "01_孩子很听话不等于关系好", 141.000),
    ("02", "02_孩子说随便是他不想说了", 124.600),
    ("03", "03_每句话都对为什么一说就错", 144.200),
    ("04", "04_孩子递过来的是三件事", 146.600),
    ("05", "05_对同事客客气气回家只剩命令", 141.873),
    ("06", "06_一日语言审计四个问题", 145.800),
    ("07", "07_道歉最难的不是对不起", 114.800),
    ("08", "08_旧账说清楚四个动作", 156.500),
    ("09", "09_先修关系会不会把孩子惯坏", 161.200),
    ("10", "10_关系缓和后规则怎么写才能执行", 126.400),
    ("11", "11_情感账户不是交易", 114.600),
    ("12", "12_有些边界不能等关系变好", 182.833),
]
RATIOS = [0.30, 0.55, 0.75]

for no, dirname, dur in CLIPS:
    mp4 = os.path.join(BASE, dirname, "_成品", "_旧版本", f"成片_{no}_无封面卡.mp4")
    if not os.path.isfile(mp4):
        print(f"[MISS] {no} {mp4}")
        continue
    for i, r in enumerate(RATIOS):
        at = dur * r
        out = os.path.join(OUT, f"{no}_{i+1}.jpg")
        cmd = [FFMPEG, "-y", "-ss", f"{at:.1f}", "-i", mp4,
               "-frames:v", "1", "-q:v", "2", out]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"[frame] {no} t={at:.1f}s -> {os.path.basename(out)} exists={os.path.exists(out)}")
print("done")
