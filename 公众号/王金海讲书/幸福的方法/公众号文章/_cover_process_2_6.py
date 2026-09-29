# -*- coding: utf-8 -*-
"""第2-6篇封面后处理：裁2.35:1、去右下AI水印(水印约 y>945,x>1380)、压<=200KB。
逐篇指定源文件与垂直裁切窗口(y0,y1)，原则：保住人物头顶 + 底部越过水印。"""
from PIL import Image
import os

RATIO = 2.35
H = 654  # 满宽1536对应高度

# (发布包目录, 源png文件名, 输出封面名, y0, y1)
JOBS = [
    ("发布包_第2篇_等孩子考上大学就好了",
     "Warm_healing_flat_illustration_2026-09-04T02-16-42.png",
     "封面_第2篇_等孩子考上大学就好了.jpg", 300, 300+H),
    ("发布包_第3篇_打游戏专注写作业喊累",
     "Warm_healing_flat_storybook_il_2026-09-04T02-20-31.png",
     "封面_第3篇_打游戏专注写作业喊累.jpg", 10, 10+H),
    ("发布包_第4篇_又要优秀又要快乐",
     "Warm_healing_flat_storybook_il_2026-09-04T02-25-25.png",
     "封面_第4篇_又要优秀又要快乐.jpg", 291, 291+H),
    ("发布包_第5篇_你脸上有没有光",
     "Warm_healing_flat_illustration_2026-09-04T02-18-08.png",
     "封面_第5篇_你脸上有没有光.jpg", 250, 250+H),
    ("发布包_第6篇_幸福是练出来的",
     "Warm_healing_flat_illustration_2026-09-04T02-18-38.png",
     "封面_第6篇_幸福是练出来的.jpg", 250, 250+H),
]

def save_under(img, out_path, limit_kb=200):
    q = 88
    while q >= 40:
        img.convert("RGB").save(out_path, "JPEG", quality=q, optimize=True, progressive=True)
        kb = os.path.getsize(out_path)/1024
        if kb <= limit_kb:
            return kb, q
        q -= 8
    return os.path.getsize(out_path)/1024, q

base = os.path.dirname(os.path.abspath(__file__))
for folder, src, out, y0, y1 in JOBS:
    p = os.path.join(base, folder, src)
    img = Image.open(p)
    w, h = img.size
    y1 = min(y1, h)
    cropped = img.crop((0, y0, w, y1))
    cw, ch = cropped.size
    # 校正比例：若偏窄则上下微调
    if abs(cw/ch - RATIO) > 0.02:
        nh = int(round(cw/RATIO))
        top = max(0, (ch-nh)//2)
        cropped = cropped.crop((0, top, cw, top+nh))
    outp = os.path.join(base, folder, out)
    kb, q = save_under(cropped, outp)
    # 右下水印复检区
    cw2, ch2 = cropped.size
    cropped.convert("RGB").crop((cw2-300, ch2-120, cw2, ch2)).resize((600, 240)).save(
        os.path.join(base, folder, "_chk_corner.png"))
    print("OK", out, cropped.size, "比例%.2f" % (cropped.size[0]/cropped.size[1]),
          "%.0fKB q=%d" % (kb, q), "裁切y=%d-%d" % (y0, y1))
