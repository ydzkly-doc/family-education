# -*- coding: utf-8 -*-
"""方案③ 米雾压实拍封面：月考成片抽帧 + 纵向米雾 + A+C 排版。
出 01 一条的 9:16 与 1:1 各一张，供用户看效果。
"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = r"D:\个人资料\家庭教育"
SRC = os.path.join(ROOT, "_帧候选", "01_a.jpg")
OUT = os.path.join(ROOT, "公众号", "手机方案", "视频号文案_v4", "_封面样张_A+C_20261011")
os.makedirs(OUT, exist_ok=True)

FB = r"C:\Windows\Fonts\msyhbd.ttc"
FR = r"C:\Windows\Fonts\msyh.ttc"
def f(p, s): return ImageFont.truetype(p, s)

INK = (43, 43, 43)
WARM_DEEP = (168, 85, 31)
MUTE = (120, 116, 108)
PAPER = (247, 242, 232)
BLUE = "#378ADD"

def tw(d, s, fp):
    b = d.textbbox((0, 0), s, font=fp); return b[2]-b[0]

def vertical_mist(w, h, alpha_top=228, alpha_mid=150, alpha_bot=70, split=0.45):
    """纵向米雾：上浓下压，中间过渡；人物在中下，底部最透。返回 RGBA 层。
    split 越小，浓雾越早散开，给方版中部人脸让清晰度。"""
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = layer.load()
    for y in range(h):
        t = y / h
        if t < split:
            a = alpha_top + (alpha_mid - alpha_top) * (t / split)
        else:
            a = alpha_mid + (alpha_bot - alpha_mid) * ((t - split) / (1 - split))
        for x in range(w):
            px[x, y] = (PAPER[0], PAPER[1], PAPER[2], int(a))
    return layer

def build(size, main_lines, sub, tag, num, square=False, out=""):
    W, H = size
    base = Image.open(SRC).convert("RGB")
    # cover 缩放铺满 + 居中裁切
    bw, bh = base.size
    scale = max(W/bw, H/bh)
    nw, nh = int(bw*scale)+1, int(bh*scale)+1
    base = base.resize((nw, nh), Image.LANCZOS)
    # 人物居中偏下：裁切时水平居中，垂直让人物落在下 2/3
    # 方版纵向空间短，取更靠下的取景（crop 偏置更大），把人脸压到画面下部避让标题
    x0 = (nw - W)//2
    crop_bias = 0.55 if not square else 0.55
    y0 = max(0, min(nh - H, int((nh - H)*crop_bias)))
    base = base.crop((x0, y0, x0+W, y0+H))
    base = base.filter(ImageFilter.GaussianBlur(1.2))   # 轻微柔化背景
    base = base.convert("RGBA")

    if square:
        # 方版＝朋友圈分享位（已有朋友圈文案）：只留提问主标，人脸完整露出。
        # 取景偏上保留人物原本构图；米雾只在顶部托一条标题带。
        mist = vertical_mist(W, H, alpha_top=240, alpha_mid=120, alpha_bot=10, split=0.30)
        img = Image.alpha_composite(base, mist).convert("RGB")
        d = ImageDraw.Draw(img)
        f_main = f(FB, 86)
        lh, y = 114, 96
        for ln in main_lines:
            lw = tw(d, ln, f_main)
            d.text(((W-lw)//2, y), ln, font=f_main, fill=INK)
            y += lh
        img.save(out, "PNG")
        print("[write]", out)
        return

    mist = vertical_mist(W, H, alpha_top=232, alpha_mid=150, alpha_bot=44)
    img = Image.alpha_composite(base, mist).convert("RGB")
    d = ImageDraw.Draw(img)

    # ---- 竖版完整版式：色条 + 系列名 + 编号 + 主标 + 副标 ----
    d.rectangle([0, 0, W, 26], fill=BLUE)
    f_tag, f_num = f(FR, 40), f(FB, 58)
    d.text((72, 88), tag, font=f_tag, fill=MUTE)
    nw_ = tw(d, num, f_num)
    d.text((W-72-nw_, 72), num, font=f_num, fill=BLUE)
    d.line([72, 170, W-72, 170], fill=(214, 208, 196), width=2)
    f_main = f(FB, 112)
    lh, y = 152, 360

    # A 主标
    for ln in main_lines:
        lw = tw(d, ln, f_main)
        d.text(((W-lw)//2, y), ln, font=f_main, fill=INK)
        y += lh

    # A 副标胶囊
    f_sub = f(FB, 52)
    px_, py_ = 44, 24
    sw = tw(d, sub, f_sub)
    bw_, bh_ = sw+px_*2, 52+py_*2-16
    bx, by = (W-bw_)//2, y+24
    d.rounded_rectangle([bx, by, bx+bw_, by+bh_], radius=bh_//2, fill=(250, 236, 231))
    d.text((bx+px_, by+py_-8), sub, font=f_sub, fill=WARM_DEEP)

    img.save(out, "PNG")
    print("[write]", out)

MAIN = ["玩了五个小时，", "就算成瘾吗？"]
SUB = "时长不是成瘾判据"
build((1080, 1920), MAIN, SUB, "孩子与手机 · 33讲", "01",
      out=os.path.join(OUT, "封面样张_01_米雾_9x16.png"))
build((1080, 1080), MAIN, SUB, "孩子与手机 · 33讲", "01", square=True,
      out=os.path.join(OUT, "封面样张_01_米雾_1x1.png"))
print("done")
