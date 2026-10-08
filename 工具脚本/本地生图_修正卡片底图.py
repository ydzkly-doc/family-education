import os
from PIL import Image, ImageFilter, ImageEnhance

gen  = r"D:\local-imagegen\out"
repo = r"D:\个人资料\家庭教育\_tmp_imagegen"

def cover_resize(im, w, h):
    """按 cover 方式缩放后居中裁切，保证无黑边"""
    s = max(w / im.width, h / im.height)
    nw, nh = int(im.width * s + 0.5), int(im.height * s + 0.5)
    im = im.resize((nw, nh), Image.LANCZOS)
    return im.crop(((nw - w) // 2, (nh - h) // 2, (nw - w) // 2 + w, (nh - h) // 2 + h))

def save_under(img, path, limit_kb, start_q=94):
    q = start_q
    while q >= 40:
        img.save(path, "JPEG", quality=q, optimize=True)
        if os.path.getsize(path) <= limit_kb * 1024:
            break
        q -= 4
    return q, os.path.getsize(path) // 1024

# --- 卡片底图 3:4 900x1200，先 cover 裁切再柔化 ---
c = Image.open(os.path.join(gen, "shot02_windowsill.png")).convert("RGB")
cb = cover_resize(c, 900, 1200).filter(ImageFilter.GaussianBlur(6))
cb = ImageEnhance.Brightness(cb).enhance(0.85)

# --- 封面 2.35:1 ---
im = Image.open(os.path.join(gen, "shot01_doorway.png")).convert("RGB")
W, H = 1200, 511
canvas = Image.new("RGB", (W, H))
bg = cover_resize(im, W, H).filter(ImageFilter.GaussianBlur(48))
canvas.paste(ImageEnhance.Brightness(bg).enhance(0.72), (0, 0))
canvas.paste(im.resize((H, H), Image.LANCZOS), ((W - H) // 2, 0))

# --- 只写仓库内（仓库外受限模式下不可写）---
os.makedirs(repo, exist_ok=True)
q1, kb1 = save_under(cb, os.path.join(repo, "卡片底图_3x4_柔化.jpg"), 100, start_q=88)
q2, kb2 = save_under(canvas, os.path.join(repo, "封面_235x1_成品.jpg"), 200, start_q=94)
print("CARD_OK", cb.size, kb1, "KB q=", q1)
print("COVER_OK", canvas.size, kb2, "KB q=", q2)
