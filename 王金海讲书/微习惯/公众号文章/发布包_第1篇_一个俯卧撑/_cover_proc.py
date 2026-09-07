# -*- coding: utf-8 -*-
"""微习惯封面后处理：1536x1024 -> 裁 2.35:1 中央宽幅带(1536x654)，顺带切掉右下角AI水印，再压到<=200KB。
   用法: python _cover_proc.py <源png> <输出jpg> [目标高(默认654)]"""
import sys
from PIL import Image

src, dst = sys.argv[1], sys.argv[2]
target_h = int(sys.argv[3]) if len(sys.argv) > 3 else 654  # 1536/654 ≈ 2.349 ≈ 2.35:1

im = Image.open(src).convert("RGB")
w, h = im.size
# 水印在原图右下 y>945、x>1380；底部裁切线取 y 使底边 <=945
# 2.35:1 中央带：高 target_h，垂直居中略偏上（保书/嫩芽；书在下半，故裁切带往下放一点）
y0 = 330            # 起点，控制保头/保书
y1 = y0 + target_h  # =984 -> 超过945 会含水印，需上移
# 保证 y1 <= 940 以切净水印
if y1 > 940:
    y1 = 940
    y0 = y1 - target_h
crop = im.crop((0, y0, w, y1))
# 缩放到标准 1536x654
crop = crop.resize((1536, 654), Image.LANCZOS)

# 渐进压缩到 <=200KB
q = 90
while q >= 55:
    crop.save(dst, "JPEG", quality=q, optimize=True)
    import os
    if os.path.getsize(dst) <= 200 * 1024:
        break
    q -= 5
import os
print("out:", dst, crop.size, "quality:", q, "%.0fKB" % (os.path.getsize(dst)/1024))
