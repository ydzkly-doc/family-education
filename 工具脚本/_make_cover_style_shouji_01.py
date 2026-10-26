# -*- coding: utf-8 -*-
"""手机方案系列 · 01 封面【样式稿】（米雾纯色底，未拍摄无实拍帧）。
复用 _make_covers_gaishan.py 工艺：3:4 1080×1440 完整 A+C
  = 顶部色条 + 左上板块角标 + 右上两位编号 + 主标(两行) + 暖色副标胶囊。
主题色：手机方案雾蓝 #85B7EB（角标/编号/色条），副标暖橙字。
"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUTDIR = r"D:\个人资料\家庭教育\公众号\手机方案\视频号文案_v4\_封面样式稿_20261026"
os.makedirs(OUTDIR, exist_ok=True)

FB = r"C:\Windows\Fonts\msyhbd.ttc"
FR = r"C:\Windows\Fonts\msyh.ttc"
def f(p, s): return ImageFont.truetype(p, s)

INK = (43, 43, 43)
MUTE = (120, 116, 108)
PAPER = (247, 242, 232)      # 米雾底
PILL_BG = (233, 240, 248)    # 雾蓝系浅底胶囊
RULE = (214, 208, 196)

BOARD = "#85B7EB"            # 手机方案雾蓝（色条/角标序号）
SUB_INK = (52, 92, 138)      # 副标深蓝字

# 01 试样：板块「看清问题」+ 序号 01；主标两行；副标取金句
TAG_A = "孩子与手机"   # 细体
TAG_SEP = "--"
TAG_B = "看清问题"     # 加粗
NO = "01"
MAIN = ["玩了五个小时，", "就算成瘾吗？"]
SUB = "玩得久，不等于成瘾"

# 副标胶囊配色方案（底, 字）
PILL_SCHEMES = {
    "A_雾蓝原案": ((233, 240, 248), (52, 92, 138)),
    "B_暖橙对照": ((250, 236, 231), (168, 85, 31)),
    "C_雾蓝深底": ((214, 230, 246), (31, 64, 104)),
    "D_雾蓝实底白字": ((133, 183, 235), (255, 255, 255)),
}


def tw(d, s, fp):
    b = d.textbbox((0, 0), s, font=fp)
    return b[2] - b[0]


def vertical_mist(w, h, alpha_top, alpha_mid, alpha_bot, split):
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


def draw_tag(d, x, y):
    """左上板块角标：孩子与手机--看清问题（看清问题加粗），分段绘制。"""
    f_reg = f(FR, 34)
    f_bd = f(FB, 36)
    d.text((x, y + 2), TAG_A, font=f_reg, fill=MUTE)
    x += tw(d, TAG_A, f_reg)
    d.text((x, y + 2), TAG_SEP, font=f_reg, fill=MUTE)
    x += tw(d, TAG_SEP, f_reg)
    d.text((x, y), TAG_B, font=f_bd, fill=INK)


def build_34(scheme_name, pill_bg, pill_ink, out_name):
    W, H = 1080, 1440
    base = Image.new("RGBA", (W, H), (PAPER[0], PAPER[1], PAPER[2], 255))
    mist = vertical_mist(W, H, 255, 235, 200, 0.5)
    img = Image.alpha_composite(base, mist).convert("RGB")
    d = ImageDraw.Draw(img)

    d.rectangle([0, 0, W, 20], fill=BOARD)
    draw_tag(d, 56, 62)
    nw_ = tw(d, NO, f(FB, 50))
    d.text((W - 56 - nw_, 52), NO, font=f(FB, 50), fill=BOARD)
    d.line([56, 132, W - 56, 132], fill=RULE, width=2)

    n = len(MAIN)
    size = 96
    while size > 54:
        f_try = f(FB, size)
        if max(tw(d, ln, f_try) for ln in MAIN) <= 920:
            break
        size -= 4
    f_main = f(FB, size)
    lh = int(size * 1.22)
    y = 320
    for ln in MAIN:
        lw = tw(d, ln, f_main)
        d.text(((W - lw) // 2, y), ln, font=f_main, fill=INK)
        y += lh

    f_sub = f(FB, 44)
    px_, py_ = 38, 18
    sw = tw(d, SUB, f_sub)
    bw_, bh_ = sw + px_ * 2, 44 + py_ * 2 - 14
    bx, by = (W - bw_) // 2, y + 24
    d.rounded_rectangle([bx, by, bx + bw_, by + bh_], radius=bh_ // 2, fill=pill_bg)
    d.text((bx + px_, by + py_ - 7), SUB, font=f_sub, fill=pill_ink)

    out = os.path.join(OUTDIR, out_name)
    img.save(out, "PNG")
    print("[3:4 ]", out)


if __name__ == "__main__":
    for name, (bg, ink) in PILL_SCHEMES.items():
        build_34(name, bg, ink, f"封面样式_01_{name}.png")
    print("done")
