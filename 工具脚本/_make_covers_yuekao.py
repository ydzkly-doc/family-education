# -*- coding: utf-8 -*-
"""系列封面批量生成器（米雾实拍底 · A+C · 两载体分工）。
按 2026-10-11 定稿标准：
  9:16 = 完整 A+C（板块色条 + 角标系列名 + 编号 + 提问主标两行 + 暖色副标胶囊）
  1:1  = 主标 only（去色条/系列名/编号/副标，浓雾压顶30%，整脸露出）
底帧 = 各条成片自选的实拍帧（已目挑，无字幕、表情平和、上方留白足）。
本次：第一次月考对话方案 5 讲。
"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

ROOT = r"D:\个人资料\家庭教育"
FRAMEDIR = os.path.join(ROOT, "_帧候选_月考")
OUTDIR = os.path.join(ROOT, "公众号", "第一次月考对话方案", "视频号文案", "_新封面_米雾_20261011")
os.makedirs(OUTDIR, exist_ok=True)

FB = r"C:\Windows\Fonts\msyhbd.ttc"
FR = r"C:\Windows\Fonts\msyh.ttc"
def f(p, s): return ImageFont.truetype(p, s)

INK = (43, 43, 43)
WARM_DEEP = (168, 85, 31)
MUTE = (120, 116, 108)
PAPER = (247, 242, 232)
PILL_BG = (250, 236, 231)
RULE = (214, 208, 196)

# 第一次月考系列：统一暖赭色（与家庭暖光/棕衣协调，低饱和）
BOARD = "#B0794E"

SERIES = "第一次月考 · 5讲"

# no -> (底帧文件, 主标分行, 副标)
# 主标分行原则：按意群在标点后断，每行字数尽量均衡，避免孤字/顶边。
ITEMS = {
    "01": ("01_1.jpg", ["成绩还没出，", "我先管住了嘴"], "忍住别问，给孩子底气"),
    "02": ("02_1.jpg", ["我就不是", "那块料？"], "比分数更要紧的一句话"),
    "03": ("03_2.jpg", ["考好了，", "第一句说啥？"], "考好先接住，别泼冷水"),
    "04": ("04_2.jpg", ["看到分数，", "火一下上来？"], "火上来，先离开现场"),
    "05": ("05_3.jpg", ["家长会，", "是判决，", "还是结盟？"], "去结盟，不是领判决"),
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


def load_base(frame, W, H, crop_bias=0.55):
    base = Image.open(os.path.join(FRAMEDIR, frame)).convert("RGB")
    bw, bh = base.size
    scale = max(W / bw, H / bh)
    nw, nh = int(bw * scale) + 1, int(bh * scale) + 1
    base = base.resize((nw, nh), Image.LANCZOS)
    x0 = (nw - W) // 2
    y0 = max(0, min(nh - H, int((nh - H) * crop_bias)))
    base = base.crop((x0, y0, x0 + W, y0 + H))
    base = base.filter(ImageFilter.GaussianBlur(1.2))
    # 轻调色：白天窗光底图偏白偏平 → 微压亮度、提对比、微暖，贴近夜拍暖光质感
    base = ImageEnhance.Brightness(base).enhance(0.95)
    base = ImageEnhance.Contrast(base).enhance(1.10)
    base = ImageEnhance.Color(base).enhance(1.06)
    base = base.convert("RGBA")
    return base


def build_916(no, frame, main_lines, sub, out):
    # 视频号封面实际展示窗 = 3:4（1080×1440），9:16 会被微信居中裁掉上下丢角标。
    W, H = 1080, 1440
    base = load_base(frame, W, H)
    mist = vertical_mist(W, H, 232, 150, 44, 0.48)
    img = Image.alpha_composite(base, mist).convert("RGB")
    d = ImageDraw.Draw(img)

    d.rectangle([0, 0, W, 20], fill=BOARD)
    d.text((56, 64), SERIES, font=f(FR, 34), fill=MUTE)
    nw_ = tw(d, no, f(FB, 50))
    d.text((W - 56 - nw_, 52), no, font=f(FB, 50), fill=BOARD)
    d.line([56, 132, W - 56, 132], fill=RULE, width=2)

    # 主标：按最长行自动缩字号（安全宽 920）；3:4 画面矮，整块文字上提、收行距，
    # 给人物头部让位（副标胶囊底部须在头顶以上）。
    n = len(main_lines)
    size = 96 if n == 2 else 78
    while size > 54:
        f_try = f(FB, size)
        if max(tw(d, ln, f_try) for ln in main_lines) <= 920:
            break
        size -= 4
    f_main = f(FB, size)
    lh = int(size * (1.22 if n == 2 else 1.16))
    y = 208 if n == 2 else 172
    for ln in main_lines:
        lw = tw(d, ln, f_main)
        d.text(((W - lw) // 2, y), ln, font=f_main, fill=INK)
        y += lh

    f_sub = f(FB, 44)
    px_, py_ = 38, 18
    sw = tw(d, sub, f_sub)
    bw_, bh_ = sw + px_ * 2, 44 + py_ * 2 - 14
    bx, by = (W - bw_) // 2, y + 16
    d.rounded_rectangle([bx, by, bx + bw_, by + bh_], radius=bh_ // 2, fill=PILL_BG)
    d.text((bx + px_, by + py_ - 7), sub, font=f_sub, fill=WARM_DEEP)

    img.save(out, "PNG")
    print("[3:4 ]", out)


def build_1x1(no, frame, main_lines, sub, out):
    W, H = 1080, 1080
    base = load_base(frame, W, H)
    mist = vertical_mist(W, H, 240, 120, 10, 0.30)
    img = Image.alpha_composite(base, mist).convert("RGB")
    d = ImageDraw.Draw(img)

    # 主标压顶：按最长行自适应字号（安全宽 936）；行数越多字号越小、越上移，
    # 保证整组标题落在顶部浓雾带内、不压额头（三行需在约 y=340 前结束）。
    n = len(main_lines)
    start_size = 88 if n == 2 else 74
    size = start_size
    while size > 44:
        f_try = f(FB, size)
        if max(tw(d, ln, f_try) for ln in main_lines) <= 936:
            break
        size -= 4
    f_main = f(FB, size)
    lh = int(size * (1.30 if n == 2 else 1.18))
    y = 78 if n == 2 else 56
    for ln in main_lines:
        lw = tw(d, ln, f_main)
        d.text(((W - lw) // 2, y), ln, font=f_main, fill=INK)
        y += lh

    img.save(out, "PNG")
    print("[1:1 ]", out)


def build_card_9x16(no, frame, main_lines, sub, out):
    """片头 2 秒封面卡：9:16 满屏（1080×1920），含完整 A+C。
    与后台上传的 3:4 是两套——片头卡是视频第 1 帧、须铺满全屏无黑边。
    """
    W, H = 1080, 1920
    base = load_base(frame, W, H)
    mist = vertical_mist(W, H, 232, 150, 44, 0.45)
    img = Image.alpha_composite(base, mist).convert("RGB")
    d = ImageDraw.Draw(img)

    d.rectangle([0, 0, W, 26], fill=BOARD)
    d.text((72, 88), SERIES, font=f(FR, 40), fill=MUTE)
    nw_ = tw(d, no, f(FB, 58))
    d.text((W - 72 - nw_, 72), no, font=f(FB, 58), fill=BOARD)
    d.line([72, 170, W - 72, 170], fill=RULE, width=2)

    n = len(main_lines)
    size = 112 if n == 2 else 92
    while size > 60:
        f_try = f(FB, size)
        if max(tw(d, ln, f_try) for ln in main_lines) <= 900:
            break
        size -= 4
    f_main = f(FB, size)
    lh = int(size * 1.34)
    y = 360 if n == 2 else 300
    for ln in main_lines:
        lw = tw(d, ln, f_main)
        d.text(((W - lw) // 2, y), ln, font=f_main, fill=INK)
        y += lh

    f_sub = f(FB, 52)
    px_, py_ = 44, 24
    sw = tw(d, sub, f_sub)
    bw_, bh_ = sw + px_ * 2, 52 + py_ * 2 - 16
    bx, by = (W - bw_) // 2, y + 24
    d.rounded_rectangle([bx, by, bx + bw_, by + bh_], radius=bh_ // 2, fill=PILL_BG)
    d.text((bx + px_, by + py_ - 8), sub, font=f_sub, fill=WARM_DEEP)

    img.save(out, "PNG")
    print("[card9:16]", out)


for no, (frame, main_lines, sub) in ITEMS.items():
    build_916(no, frame, main_lines, sub,
              os.path.join(OUTDIR, f"封面_{no}.png"))
    build_1x1(no, frame, main_lines, sub,
              os.path.join(OUTDIR, f"封面_{no}_1x1.png"))

# 片头卡：仅 03/04/05（01/02 已发布不动），9:16 满屏
CARD_DIR = os.path.join(OUTDIR, "片头卡9x16")
os.makedirs(CARD_DIR, exist_ok=True)
for no in ("03", "04", "05"):
    frame, main_lines, sub = ITEMS[no]
    build_card_9x16(no, frame, main_lines, sub,
                    os.path.join(CARD_DIR, f"封面卡_{no}_9x16.png"))
print("done")
