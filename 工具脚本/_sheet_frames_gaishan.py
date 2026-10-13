# -*- coding: utf-8 -*-
"""把每条 3 张候选帧横拼成一张对照图，便于目挑封面底图。"""
import os
from PIL import Image

D = r"D:\个人资料\家庭教育\_帧候选_改善"
CW, CH = 400, 711  # 单帧缩略
for i in range(1, 13):
    no = f"{i:02d}"
    ims = []
    for k in (1, 2, 3):
        p = os.path.join(D, f"{no}_{k}.jpg")
        if os.path.exists(p):
            ims.append(Image.open(p).convert("RGB").resize((CW, CH), Image.LANCZOS))
    if not ims:
        continue
    sheet = Image.new("RGB", (CW * len(ims), CH), (30, 30, 30))
    for idx, im in enumerate(ims):
        sheet.paste(im, (idx * CW, 0))
    out = os.path.join(D, f"_拼_{no}.jpg")
    sheet.save(out, "JPEG", quality=88)
    print("sheet", out, sheet.size)
print("done")
