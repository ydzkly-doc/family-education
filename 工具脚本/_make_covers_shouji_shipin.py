# -*- coding: utf-8 -*-
"""手机方案系列封面生成器（米雾实拍底 · A+C · 三版）。
按 2026-10-17 定稿口径：
  封面_NN.png        3:4 1080x1440 完整 A+C → 后台上传
  封面卡_NN_9x16.png 9:16 1080x1920 完整 A+C 满屏 → 片头封面卡参考
  封面_NN_1x1.png    1:1 1080x1080 主标 only → 朋友圈
板块色：雾蓝 #6E97C9。底帧＝各条成片目挑实拍帧（无字幕遮脸、睁眼、上方留白足）。
常驻标题版底帧顶部带字幕 → 米雾需 cap 盖死区压掉。
"""
import os, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

ROOT = r"D:\个人资料\家庭教育\公众号\手机方案\视频号文案_v4"
FB = r"C:\Windows\Fonts\msyhbd.ttc"
FR = r"C:\Windows\Fonts\msyh.ttc"
def f(p, s): return ImageFont.truetype(p, s)

INK = (43, 43, 43)
WARM_DEEP = (62, 96, 138)       # 雾蓝系深字（浅雾底上清楚、低饱和）
MUTE = (110, 120, 132)
PAPER = (247, 242, 232)
PILL_BG = (232, 239, 247)       # 雾蓝浅胶囊底
RULE = (206, 214, 224)
BOARD = "#6E97C9"
SERIES = "孩子与手机"

# no -> (板块, 底帧绝对路径, 主标分行, 副标)
ITEMS = {
    "01": ("看清问题",
           r"D:\个人资料\家庭教育\公众号\手机方案\视频号文案_v4\01_玩得久不等于成瘾\_成品\_过程文件\frame_01.png",
           ["玩了五个小时，", "就算成瘾吗？"], "玩得久不等于成瘾"),
    "02": ("看清问题",
           r"D:\个人资料\家庭教育\公众号\手机方案\视频号文案_v4\02_超过约定不等于有病\_成品\_过程文件\frame_02.png",
           ["用超了约定，", "就是出大问题吗？"], "超过约定不等于有病"),
    "03": ("看清问题",
           r"D:\个人资料\家庭教育\公众号\手机方案\视频号文案_v4\03_不是手机抢走了学习\_成品\_过程文件\frame_03.png",
           ["他盯着手机，", "其实是先学不动了"], "不是手机抢走了学习"),
    "04": ("看清问题",
           r"D:\个人资料\家庭教育\公众号\手机方案\视频号文案_v4\04_太久没有赢过\_成品\_过程文件\frame_04.png",
           ["不努力，", "还是没赢过？"], "太久没有赢过"),
    "05": ("看清问题",
           r"D:\个人资料\家庭教育\公众号\手机方案\视频号文案_v4\05_游戏为什么比写作业容易上手\_成品\_过程文件\frame_05.png",
           ["打游戏能坐住，", "写作业就泄气？"], "游戏为什么比写作业容易上手"),
    "06": ("看懂机制",
           r"D:\个人资料\家庭教育\公众号\手机方案\视频号文案_v4\06_再一局为什么停不下来\_成品\_过程文件\frame_06.png",
           ["说好再玩一局，", "怎么一局又一局？"], "再一局为什么停不下来"),
    "07": ("看懂机制",
           r"D:\个人资料\家庭教育\公众号\手机方案\视频号文案_v4\07_短视频为什么没有看完\_成品\_过程文件\frame_07.png",
           ["手指一划，", "半小时就没了"], "短视频为什么没有看完"),
    "08": ("看懂机制",
           r"D:\个人资料\家庭教育\公众号\手机方案\视频号文案_v4\08_孩子一难受就拿手机\_成品\_过程文件\frame_08.png",
           ["他是偷懒，", "还是躲难？"], "孩子一难受就拿手机"),
    "09": ("看懂机制",
           r"D:\个人资料\家庭教育\公众号\手机方案\视频号文案_v4\09_该管到什么程度\_成品\_过程文件\frame_09.png",
           ["别只问玩多久，", "先看有没有进有出"], "该管到什么程度"),
    "10": ("看懂机制",
           r"D:\个人资料\家庭教育\公众号\手机方案\视频号文案_v4\10_他舍不得的不是游戏是那群人\_成品\_过程文件\frame_10.png",
           ["他喊\"五缺一\"，", "舍不得的真是游戏？"], "他舍不得的不是游戏是那群人"),
    "11": ("看懂机制",
           r"D:\个人资料\家庭教育\公众号\手机方案\视频号文案_v4\11_卸载了归属感去哪补\_成品\_过程文件\frame_11.png",
           ["真卸载了，", "那群人等他的位置去哪补？"], "卸载了归属感去哪补"),
    "12": ("先救身体",
           r"D:\个人资料\家庭教育\公众号\手机方案\视频号文案_v4\12_别问玩多久问手机替他解决了什么\_成品\_过程文件\frame_12.png",
           ["别问玩多久，", "问手机替他解决了什么"], "别问玩多久问手机替他解决了什么"),
}

def tw(d, s, fp):
    b = d.textbbox((0, 0), s, font=fp)
    return b[2] - b[0]

def vertical_mist(w, h, alpha_top, alpha_mid, alpha_bot, split, cap=0.0, cap_a=255):
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = layer.load()
    for y in range(h):
        t = y / h
        if cap > 0 and t <= cap:
            a = cap_a
        elif t < split:
            u = (t - cap) / (split - cap) if split > cap else 1.0
            e = 0.5 - 0.5 * math.cos(math.pi * u)
            a = cap_a + (alpha_mid - cap_a) * e
        else:
            a = alpha_mid + (alpha_bot - alpha_mid) * ((t - split) / (1 - split))
        for x in range(w):
            px[x, y] = (PAPER[0], PAPER[1], PAPER[2], int(a))
    return layer

def load_base(frame, W, H, crop_bias=0.55):
    base = Image.open(frame).convert("RGB")
    bw, bh = base.size
    scale = max(W / bw, H / bh)
    nw, nh = int(bw * scale) + 1, int(bh * scale) + 1
    base = base.resize((nw, nh), Image.LANCZOS)
    x0 = (nw - W) // 2
    y0 = max(0, min(nh - H, int((nh - H) * crop_bias)))
    base = base.crop((x0, y0, x0 + W, y0 + H))
    base = base.filter(ImageFilter.GaussianBlur(1.2))
    base = ImageEnhance.Brightness(base).enhance(0.95)
    base = ImageEnhance.Contrast(base).enhance(1.10)
    base = ImageEnhance.Color(base).enhance(1.06)
    return base.convert("RGBA")

def _main_size(d, main_lines, maxw, start):
    size = start
    while size > 40:
        if max(tw(d, ln, f(FB, size)) for ln in main_lines) <= maxw:
            break
        size -= 4
    return size

def build_34(no, board, frame, main_lines, sub, out):
    W, H = 1080, 1440
    img = Image.alpha_composite(load_base(frame, W, H),
                                vertical_mist(W, H, 232, 150, 44, 0.48, cap=0.205, cap_a=255)).convert("RGB")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 20], fill=BOARD)
    d.text((56, 64), SERIES, font=f(FR, 34), fill=MUTE)
    sx = 56 + tw(d, SERIES, f(FR, 34))
    d.text((sx, 64), "--", font=f(FR, 34), fill=MUTE)
    d.text((sx + tw(d, "--", f(FR, 34)), 60), board, font=f(FB, 36), fill=INK)
    nw_ = tw(d, no, f(FB, 50))
    d.text((W - 56 - nw_, 52), no, font=f(FB, 50), fill=BOARD)
    d.line([56, 132, W - 56, 132], fill=RULE, width=2)
    n = len(main_lines)
    size = _main_size(d, main_lines, 920, 96 if n == 2 else 78)
    f_main = f(FB, size)
    lh = int(size * (1.22 if n == 2 else 1.16))
    y = 208 if n == 2 else 172
    for ln in main_lines:
        lw = tw(d, ln, f_main)
        d.text(((W - lw) // 2, y), ln, font=f_main, fill=INK)
        y += lh
    f_sub = f(FB, 44); px_, py_ = 38, 18
    sw = tw(d, sub, f_sub); bw_, bh_ = sw + px_ * 2, 44 + py_ * 2 - 14
    bx, by = (W - bw_) // 2, y + 16
    d.rounded_rectangle([bx, by, bx + bw_, by + bh_], radius=bh_ // 2, fill=PILL_BG)
    d.text((bx + px_, by + py_ - 7), sub, font=f_sub, fill=WARM_DEEP)
    img.save(out, "PNG"); print("[3:4 ]", os.path.basename(out))

def build_1x1(no, frame, main_lines, out):
    W, H = 1080, 1080
    img = Image.alpha_composite(load_base(frame, W, H),
                                vertical_mist(W, H, 240, 120, 10, 0.30)).convert("RGB")
    d = ImageDraw.Draw(img)
    n = len(main_lines)
    size = _main_size(d, main_lines, 936, 78 if n == 2 else 68)
    f_main = f(FB, size)
    lh = int(size * (1.22 if n == 2 else 1.16))
    y = 60 if n == 2 else 48
    for ln in main_lines:
        lw = tw(d, ln, f_main)
        d.text(((W - lw) // 2, y), ln, font=f_main, fill=INK)
        y += lh
    img.save(out, "PNG"); print("[1:1 ]", os.path.basename(out))

def build_card_9x16(no, board, frame, main_lines, sub, out):
    W, H = 1080, 1920
    img = Image.alpha_composite(load_base(frame, W, H),
                                vertical_mist(W, H, 232, 150, 44, 0.45, cap=0.205, cap_a=255)).convert("RGB")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 26], fill=BOARD)
    d.text((72, 88), SERIES, font=f(FR, 40), fill=MUTE)
    sx = 72 + tw(d, SERIES, f(FR, 40))
    d.text((sx, 88), "--", font=f(FR, 40), fill=MUTE)
    d.text((sx + tw(d, "--", f(FR, 40)), 84), board, font=f(FB, 42), fill=INK)
    nw_ = tw(d, no, f(FB, 58))
    d.text((W - 72 - nw_, 72), no, font=f(FB, 58), fill=BOARD)
    d.line([72, 170, W - 72, 170], fill=RULE, width=2)
    n = len(main_lines)
    size = _main_size(d, main_lines, 900, 112 if n == 2 else 92)
    f_main = f(FB, size)
    lh = int(size * 1.34)
    y = 360 if n == 2 else 300
    for ln in main_lines:
        lw = tw(d, ln, f_main)
        d.text(((W - lw) // 2, y), ln, font=f_main, fill=INK)
        y += lh
    f_sub = f(FB, 52); px_, py_ = 44, 24
    sw = tw(d, sub, f_sub); bw_, bh_ = sw + px_ * 2, 52 + py_ * 2 - 16
    bx, by = (W - bw_) // 2, y + 24
    d.rounded_rectangle([bx, by, bx + bw_, by + bh_], radius=bh_ // 2, fill=PILL_BG)
    d.text((bx + px_, by + py_ - 8), sub, font=f_sub, fill=WARM_DEEP)
    img.save(out, "PNG"); print("[card]", os.path.basename(out))

DIRMAP = {
    "01": r"01_玩得久不等于成瘾", "02": r"02_超过约定不等于有病",
    "03": r"03_不是手机抢走了学习", "04": r"04_太久没有赢过",
    "05": r"05_游戏为什么比写作业容易上手", "06": r"06_再一局为什么停不下来",
    "07": r"07_短视频为什么没有看完", "08": r"08_孩子一难受就拿手机",
    "09": r"09_该管到什么程度", "10": r"10_他舍不得的不是游戏是那群人",
    "11": r"11_卸载了归属感去哪补", "12": r"12_别问玩多久问手机替他解决了什么",
}
if __name__ == "__main__":
    for no, (board, frame, main_lines, sub) in ITEMS.items():
        if not os.path.exists(frame):
            print(f"[skip] {no} frame 不存在: {frame}")
            continue
        outdir = os.path.join(ROOT, DIRMAP[no], "_成品")
        build_34(no, board, frame, main_lines, sub, os.path.join(outdir, f"封面_{no}.png"))
        build_1x1(no, frame, main_lines, os.path.join(outdir, f"封面_{no}_1x1.png"))
        build_card_9x16(no, board, frame, main_lines, sub, os.path.join(outdir, f"封面卡_{no}_9x16.png"))
    print("done")
