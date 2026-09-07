# -*- coding: utf-8 -*-
"""微习惯系列封面批量后处理：1536x1024 -> 2.35:1(1536x654) 无字无水印 <=200KB。
   每张按主体垂直位置给裁切窗 y0；底边 y1=y0+654 且 <=940 以切净右下角水印。"""
import os
from PIL import Image

BASE = os.path.dirname(os.path.abspath(__file__))

# (发布包目录, 源png文件名, 输出封面名, 裁切起点y0)
# y0 选取：保中央主体头/尾完整；y1=y0+654<=940 去水印。
JOBS = [
    ("发布包_第2篇_别靠打鸡血",        "Warm_flat_illustration__cozy_h_2026-09-07T02-29-58.png", "封面_第2篇_别靠打鸡血.jpg",        185),
    ("发布包_第3篇_定到脸红",          "Warm_flat_illustration__cozy_h_2026-09-07T02-30-34.png", "封面_第3篇_定到脸红.jpg",          150),
    ("发布包_第4篇_四个机关",          "白板五角星_raw.png",                                      "封面_第4篇_四个机关.jpg",          286),
    ("发布包_第5篇_练5遍改5个一遍",    "Warm_flat_illustration__cozy_h_2026-09-07T02-31-02.png", "封面_第5篇_练5遍改5个一遍.jpg",    170),
]
TH = 654  # 目标高（1536/654≈2.349）

for folder, src_name, out_name, y0 in JOBS:
    src = os.path.join(BASE, folder, src_name)
    dst = os.path.join(BASE, folder, out_name)
    im = Image.open(src).convert("RGB")
    w, h = im.size  # 1536x1024
    y1 = y0 + TH
    if y1 > 940:          # 保水印切净
        y1 = 940; y0 = y1 - TH
    if y0 < 0:
        y0 = 0; y1 = TH
    crop = im.crop((0, y0, w, y1)).resize((1536, TH), Image.LANCZOS)
    q = 90
    while q >= 55:
        crop.save(dst, "JPEG", quality=q, optimize=True)
        if os.path.getsize(dst) <= 200*1024:
            break
        q -= 5
    print("%-28s y0=%3d  %s  q=%d  %.0fKB" % (out_name, y0, crop.size, q, os.path.getsize(dst)/1024))
