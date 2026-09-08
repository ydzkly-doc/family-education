# -*- coding: utf-8 -*-
# 封面候选后处理：1536x1024 -> 裁 2.35:1 (1536x654)，底部裁切线 y1<=940 去右下AI水印；压到<=200KB
from PIL import Image
import os

base = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(base, "_原始png")

jobs = [
    ("Flat_warm_editorial_illustrati_2026-09-07T14-42-05.png", "封面候选1_来电书桌.jpg"),
    ("Flat_warm_editorial_illustrati_2026-09-07T14-42-39.png", "封面候选2_手机留校.jpg"),
    ("Flat_warm_editorial_illustrati_2026-09-07T14-43-13.png", "封面候选3_等门的家.jpg"),
]

TARGET_W, TARGET_H = 1536, 654  # 2.35:1

for src_name, out_name in jobs:
    src = os.path.join(src_dir, src_name)
    im = Image.open(src).convert("RGB")
    w, h = im.size
    # 目标裁切高度按宽度比例
    crop_h = int(w / 2.35)  # ~654
    # 垂直居中偏上一点点保住主体；y1 必须 <= 945 去水印
    # 居中: y0 = (h - crop_h)//2
    y0 = (h - crop_h) // 2
    y1 = y0 + crop_h
    if y1 > 940:
        y1 = 940
        y0 = y1 - crop_h
    box = (0, y0, w, y1)
    c = im.crop(box)
    c = c.resize((TARGET_W, TARGET_H), Image.LANCZOS)
    out = os.path.join(base, out_name)
    q = 88
    while q >= 40:
        c.save(out, "JPEG", quality=q, optimize=True)
        if os.path.getsize(out) <= 200 * 1024:
            break
        q -= 6
    print(f"{out_name}: {c.size[0]}x{c.size[1]}, {os.path.getsize(out)//1024}KB, q={q}, y0={y0} y1={y1}")
