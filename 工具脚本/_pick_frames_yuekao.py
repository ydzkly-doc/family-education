# -*- coding: utf-8 -*-
"""第一次月考 5 条：从各条成片抽候选帧，供目挑封面底图。
每条在 30%/55%/75% 处各抽一帧（避开开头封面卡 0~2s 与结尾）。
"""
import os
import subprocess

FFMPEG = r"C:\Users\ZhuanZ\.workbuddy\binaries\ffmpeg\bin\ffmpeg.exe"
BASE = r"D:\个人资料\家庭教育\公众号\第一次月考对话方案\视频号文案"
OUT = r"D:\个人资料\家庭教育\_帧候选_月考"
os.makedirs(OUT, exist_ok=True)

# (编号, 目录名, 时长秒)
CLIPS = [
    ("01", "01_出分前忍住别问", 181.0),
    ("02", "02_我不是那块料", 173.9),
    ("03", "03_考好别泼冷水", 141.0),
    ("04", "04_火上来先离开", 153.2),
    ("05", "05_家长会", 195.0),
]
RATIOS = [0.30, 0.55, 0.75]

for no, dirname, dur in CLIPS:
    mp4 = os.path.join(BASE, dirname, "_成品", f"成片_{no}.mp4")
    for i, r in enumerate(RATIOS):
        at = dur * r
        out = os.path.join(OUT, f"{no}_{i+1}.jpg")
        cmd = [
            FFMPEG, "-y", "-ss", f"{at:.1f}", "-i", mp4,
            "-frames:v", "1", "-q:v", "2", out,
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"[frame] {no} t={at:.1f}s -> {out}  exists={os.path.exists(out)}")
print("done")
