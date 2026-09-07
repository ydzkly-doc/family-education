# -*- coding: utf-8 -*-
"""封面后处理：裁 2.35:1、去右下角AI水印、压<=200KB。
对每张图指定垂直裁切框（保核心意象、切掉底部水印条）。"""
from PIL import Image
import os

BASE = os.path.dirname(os.path.abspath(__file__))
RATIO = 2.35

# (源文件, 输出名, 垂直裁切：取图中 y0~y1 区段再按2.35裁宽；None=自动中央)
JOBS = [
    ("Warm_healing_flat_illustration_2026-09-04T02-06-50.png",
     "封面候选1_父亲放水杯_门口少年.jpg", "father_cup"),
    ("Warm_healing_flat_illustration_2026-09-04T02-07-21.png",
     "封面候选2_父子背影望光.jpg", "father_son_window"),
    ("Warm_healing_minimalist_flat_i_2026-09-04T02-07-47.png",
     "封面候选3_门与水杯_无人物.jpg", "door_cup"),
]

def crop_235(img, mode):
    w, h = img.size
    target_h = int(round(w / RATIO))   # 以满宽算高度 ≈654
    # 水印在原图右下角（约 y>945, x>1380）。裁切时下边界必须高于水印字顶。
    if mode in ("father_cup", "door_cup"):
        # 保住下方杯子/门：下边界取 945（水印之上），上边界=945-654=291
        y1 = 945
        y0 = y1 - target_h
        if y0 < 0:
            y0 = 0; y1 = target_h
    else:
        # 人物背影在中部：下边界也压到 945 去水印，上边界相应
        y1 = 945
        y0 = y1 - target_h
        if y0 < 0:
            y0 = 0; y1 = target_h
    return img.crop((0, y0, w, y1))

def save_under(img, out_path, limit_kb=200):
    q = 88
    while q >= 40:
        img.convert("RGB").save(out_path, "JPEG", quality=q, optimize=True, progressive=True)
        kb = os.path.getsize(out_path) / 1024
        if kb <= limit_kb:
            return kb, q
        q -= 8
    return os.path.getsize(out_path)/1024, q

for src, out, mode in JOBS:
    p = os.path.join(BASE, src)
    img = Image.open(p)
    print("源:", src, img.size)
    cropped = crop_235(img, mode)
    # 若略超宽高比，按宽再校正
    cw, ch = cropped.size
    if abs(cw/ch - RATIO) > 0.02:
        nh = int(round(cw/RATIO))
        cropped = cropped.crop((0, max(0,(ch-nh)//2), cw, max(0,(ch-nh)//2)+nh))
    outp = os.path.join(BASE, out)
    kb, q = save_under(cropped, outp)
    print("  ->", out, cropped.size, "比例 %.2f" % (cropped.size[0]/cropped.size[1]),
          "%.0fKB q=%d" % (kb, q))
