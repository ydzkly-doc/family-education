# -*- coding: utf-8 -*-
"""《改善你的亲子关系》12 条封面批量生成器（米雾实拍底 · A+C · 三载体分工）。
按 2026-10-11 定稿标准：
  3:4（1080×1440）＝后台上传封面，完整 A+C（板块色条+角标系列名+编号+提问主标+暖色副标胶囊）
  9:16（1080×1920）＝片头 2 秒封面卡，完整 A+C 满屏版（烧进成片开头）
  1:1（1080×1080）＝朋友圈方版，主标 only（去色条/系列名/编号/副标，浓雾压顶 30%，整脸露出）
底帧＝各条「无封面卡」成片目挑帧（无字幕、表情平和、上方留白足）。
工艺复用 _make_covers_yuekao.py（月考 5 条实测通过版）。
"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

ROOT = r"D:\个人资料\家庭教育"
FRAMEDIR = os.path.join(ROOT, "_帧候选_改善")
OUTDIR = os.path.join(ROOT, "公众号", "改善你的亲子关系", "视频号文案", "_新封面_米雾_20261011")
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

# 改善系列：暖陶玫（低饱和、偏红粉，区别于月考暖赭#B0794E / 手机雾蓝#85B7EB，
# 与本系列粉帘暖光底帧协调）
BOARD = "#C4756B"

SERIES = "改善你的亲子关系 · 12讲"

# no -> (底帧文件, 主标分行, 副标)
# 主标分行：按意群在标点后断；副标 8~12 字主题词。
ITEMS = {
    "01": ("01_3.jpg", ["孩子很听话，", "就说明关系好吗？"], "听话，不等于关系好"),
    "02": ("02_1.jpg", ["孩子说“随便”，", "就是没想法吗？"], "他不是没想法，是不想说了"),
    "03": ("03_2.jpg", ["我每句话都对，", "为什么一说就错？"], "说得对，不等于听得进"),
    "04": ("04_1.jpg", ["孩子递过来的，", "只是一个问题吗？"], "先接消息，再处理问题"),
    "05": ("05_1.jpg", ["对外人客客气气，", "回家只剩命令？"], "熟，不等于可以不尊重"),
    "06": ("06_1.jpg", ["我对孩子，", "只剩命令句了吗？"], "一天的话，抽出来看看"),
    "07": ("07_1.jpg", ["你说的对不起，", "孩子信了吗？"], "对不起，别急着辩护"),
    "08": ("08_1.jpg", ["这笔旧账，", "为什么结不清？"], "说到能放下，才算清"),
    "09": ("09_4.jpg", ["先修关系，", "会不会把孩子惯坏？"], "共情，不等于同意"),
    "10": ("10_3.jpg", ["一条规则，", "怎么说才好执行？"], "能执行的规则问四件事"),
    "11": ("11_2.jpg", ["情感账户不是交易，", "那是什么？"], "存进去的，是底气"),
    "12": ("12_2.jpg", ["有些事，", "能等关系变好吗？"], "安全边界，不能等"),
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
    # 白天窗光底偏白偏平 → 轻调色（月考实测值）
    base = ImageEnhance.Brightness(base).enhance(0.95)
    base = ImageEnhance.Contrast(base).enhance(1.10)
    base = ImageEnhance.Color(base).enhance(1.06)
    return base.convert("RGBA")


def build_34(no, frame, main_lines, sub, out):
    """后台上传封面：3:4（1080×1440）完整 A+C。"""
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
    print("[3:4 ]", os.path.basename(out))


def build_1x1(no, frame, main_lines, sub, out):
    """朋友圈方版：1:1 主标 only。"""
    W, H = 1080, 1080
    base = load_base(frame, W, H)
    mist = vertical_mist(W, H, 240, 120, 10, 0.30)
    img = Image.alpha_composite(base, mist).convert("RGB")
    d = ImageDraw.Draw(img)

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
    print("[1:1 ]", os.path.basename(out))


def build_card_9x16(no, frame, main_lines, sub, out):
    """片头 2 秒封面卡：9:16 满屏（1080×1920）完整 A+C。"""
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
    print("[card9:16]", os.path.basename(out))


if __name__ == "__main__":
    for no, (frame, main_lines, sub) in ITEMS.items():
        build_34(no, frame, main_lines, sub, os.path.join(OUTDIR, f"封面_{no}.png"))
        build_1x1(no, frame, main_lines, sub, os.path.join(OUTDIR, f"封面_{no}_1x1.png"))
    CARD_DIR = os.path.join(OUTDIR, "片头卡9x16")
    os.makedirs(CARD_DIR, exist_ok=True)
    for no, (frame, main_lines, sub) in ITEMS.items():
        build_card_9x16(no, frame, main_lines, sub,
                        os.path.join(CARD_DIR, f"封面卡_{no}_9x16.png"))
    print("done")
