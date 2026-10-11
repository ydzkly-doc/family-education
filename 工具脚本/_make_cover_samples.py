# -*- coding: utf-8 -*-
"""A+C 封面样张：01/16/32（9:16 1080x1920）。
设计稿阶段独立绘制（管道封面是实拍帧烧单行字，暂不支持副标/角标）。
色系对齐管道：墨字 #2B2B2B、暖橙 #C2703C、深橙 #A8551F、米底 #F7F2E8。
"""
import os
from PIL import Image, ImageDraw, ImageFont

OUT = r"D:\个人资料\家庭教育\公众号\手机方案\视频号文案_v4\_封面样张_A+C_20261011"
os.makedirs(OUT, exist_ok=True)

FB = r"C:\Windows\Fonts\msyhbd.ttc"   # 微软雅黑 Bold
FR = r"C:\Windows\Fonts\msyh.ttc"     # 常规

W, H = 1080, 1920
INK = "#2B2B2B"
WARM = "#C2703C"
WARM_DEEP = "#A8551F"
PAPER = (247, 242, 232)          # #F7F2E8 米底
MUTE = "#8A857B"

# 六板块低饱和色板（角标色条用）
BOARD = {
    0: "#B4B2A9",  # 立场·暖灰
    1: "#85B7EB",  # 破误区·雾蓝
    2: "#AFA9EC",  # 懂吸引·暮紫
    3: "#5DCAA5",  # 先看清·青芷
    4: "#E8B07A",  # 家里能改·暖砂
    5: "#ED93B1",  # 反复崩了·藕粉
    6: "#97C459",  # 交还·苔绿
}

def font(path, size):
    return ImageFont.truetype(path, size)

def text_w(d, s, f):
    b = d.textbbox((0, 0), s, font=f)
    return b[2] - b[0]

def wrap_by_width(d, s, f, maxw):
    """按视觉宽度折行（中文逐字），返回行列表。"""
    lines, cur = [], ""
    for ch in s:
        if text_w(d, cur + ch, f) <= maxw:
            cur += ch
        else:
            lines.append(cur); cur = ch
    if cur:
        lines.append(cur)
    return lines

def draw_cover(nn, board, main_lines, sub, main_is_statement=False, fname="", square=False):
    CW, CH = (1080, 1080) if square else (W, H)
    img = Image.new("RGB", (CW, CH), PAPER)
    d = ImageDraw.Draw(img)
    bc = BOARD[board]

    # —— C 系列识别层：顶部色条 ——
    d.rectangle([0, 0, CW, 26], fill=bc)

    # 角标：左「孩子与手机 · 33讲」  右 两位编号
    f_tag = font(FR, 38 if square else 40)
    d.text((72, 80 if square else 88), "孩子与手机 · 33讲", font=f_tag, fill=MUTE)
    f_num = font(FB, 56 if square else 58)
    ns = nn
    nw = text_w(d, ns, f_num)
    d.text((CW - 72 - nw, 66 if square else 72), ns, font=f_num, fill=bc)
    d.line([72, 156 if square else 168, CW - 72, 156 if square else 168],
           fill=(216, 210, 199), width=2)

    # —— A 主标：按意群显式断行 ——（方版字号略小、垂直居中偏上）
    f_main = font(FB, 96 if square else 108)
    line_h = 132 if square else 150
    total_h = len(main_lines) * line_h
    y = (470 if square else 720) - total_h // 2
    for ln in main_lines:
        lw = text_w(d, ln, f_main)
        d.text(((CW - lw) // 2, y), ln, font=f_main, fill=INK)
        y += line_h

    # —— A 副标：暖色胶囊 ——
    f_sub = font(FB, 50 if square else 52)
    pad_x, pad_y = 44, 26
    sw = text_w(d, sub, f_sub)
    box_w = sw + pad_x * 2
    box_h = 50 + pad_y * 2 - 16 if square else 52 + pad_y * 2 - 16
    bx = (CW - box_w) // 2
    by = y + 56
    d.rounded_rectangle([bx, by, bx + box_w, by + box_h], radius=box_h // 2,
                        fill=(250, 236, 231))
    d.text((bx + pad_x, by + pad_y - 8), sub, font=f_sub, fill=WARM_DEEP)

    # 底部落款（方版也保留，位置收高一点）
    f_foot = font(FR, 36)
    foot = "一个也在重启的爸爸 ·《孩子与手机》"
    fw = text_w(d, foot, f_foot)
    d.text(((CW - fw) // 2, CH - (120 if square else 150)), foot, font=f_foot, fill=MUTE)

    p = os.path.join(OUT, fname)
    img.save(p, "PNG")
    print("[write]", p)

SAMPLES = [
    ("01", 1, ["玩了五个小时，", "就算成瘾吗？"], "时长不是成瘾判据", False),
    ("16", 4, ["管手机，", "先动哪一件？"], "先把睡眠救回来", False),
    ("32", 6, ["目标，是让他", "自己管得住"], "不是替他管住手机", True),
]

for nn, bd, ml, sub, isb in SAMPLES:
    tag = "BC" if isb else "AC"
    draw_cover(nn, bd, ml, sub, main_is_statement=isb,
               fname=f"封面样张_{nn}_{tag}.png")
    draw_cover(nn, bd, ml, sub, main_is_statement=isb, square=True,
               fname=f"封面样张_{nn}_{tag}_1x1.png")

print("done")
