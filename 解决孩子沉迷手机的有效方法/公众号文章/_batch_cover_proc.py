# -*- coding: utf-8 -*-
"""批量封面后处理：1536x1024 原图 → 裁 2.35:1（1536x654）+ 去右下角 AI 水印 + 压到 200KB 内。

水印实测：约 x>1216、y>894（原图坐标），故底部裁切线必须 <= 894。
用法：python _batch_cover_proc.py
"""
import os, glob, json
from PIL import Image

BASE = os.path.dirname(os.path.abspath(__file__))
W, H = 1536, 1024
OUT_H = 654
TOP = 236
BOTTOM = TOP + OUT_H  # 890 < 894 → 水印切净

# (篇号, 包名, 输出封面名)
JOBS = [
    (2, "发布包_第2篇_那条路是我铺的", "封面_第2篇_那条路是我铺的.jpg"),
    (3, "发布包_第3篇_没台阶下", "封面_第3篇_没台阶下.jpg"),
    (4, "发布包_第4篇_我一开口就推远", "封面_第4篇_我一开口就推远.jpg"),
    (5, "发布包_第5篇_网课差在哪", "封面_第5篇_网课差在哪.jpg"),
    (6, "发布包_第6篇_三方面谈", "封面_第6篇_三方面谈.jpg"),
    (7, "发布包_第7篇_一张纸的约定", "封面_第7篇_一张纸的约定.jpg"),
    (8, "发布包_第8篇_有人等他", "封面_第8篇_有人等他.jpg"),
]


def compress(im, path, limit_kb=200):
    q = 92
    while q >= 40:
        im.save(path, "JPEG", quality=q, optimize=True, progressive=True)
        if os.path.getsize(path) <= limit_kb * 1024:
            return q, os.path.getsize(path)
        q -= 6
    return q, os.path.getsize(path)


report = []
for n, pkg, out_name in JOBS:
    d = os.path.join(BASE, pkg)
    srcs = sorted(glob.glob(os.path.join(d, "_封面原始png", "*.png")))
    if not srcs:
        print(f"❌ 第{n}篇 无原始图")
        continue
    src = srcs[0]
    im = Image.open(src).convert("RGB")
    cropped = im.crop((0, TOP, W, BOTTOM))
    out = os.path.join(d, out_name)
    q, size = compress(cropped, out)
    report.append((n, out_name, cropped.size, q, size))
    print(f"✅ 第{n}篇 {out_name}  {cropped.size[0]}x{cropped.size[1]}  q={q}  {size/1024:.0f}KB")

# 逐张生成右下角目检小图（放大 2 倍，确认无水印残留）
print("\n--- 目检小图 ---")
for n, pkg, _ in JOBS:
    d = os.path.join(BASE, pkg)
    jpgs = [f for f in glob.glob(os.path.join(d, "封面_*.jpg"))]
    if not jpgs:
        continue
    im = Image.open(jpgs[0])
    c = im.crop((im.width - 340, im.height - 130, im.width, im.height))
    c = c.resize((c.width * 2, c.height * 2))
    p = os.path.join(d, f"_chk_第{n}篇_右下角.png")
    c.save(p)
    print(" ", os.path.basename(p))

print(f"\n完成 {len(report)}/7 张")
