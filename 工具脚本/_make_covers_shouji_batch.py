# -*- coding: utf-8 -*-
"""手机方案系列 33 条封面【样式稿】批量生成（米雾纯色底，未拍摄占位）。
工艺复用 _make_covers_gaishan.py；3:4 1080×1440 完整 A+C。
角标：孩子与手机--板块名(加粗)；00/32 无板块则用「孩子与手机」+ 角色。
副标胶囊：B 暖橙方案（底 #FAECE7 / 字 #A8551F）。
主标＝md 封面大字（已含板块前缀，这里去掉前缀只留问题本体，板块已在角标体现）。
副标＝md 金句大字卡首句（去标点截断）。
"""
import os, re, glob
from PIL import Image, ImageDraw, ImageFont

ROOT = r"D:\个人资料\家庭教育\公众号\手机方案\视频号文案_v4"
OUTDIR = os.path.join(ROOT, "_封面样式稿_20261026")
os.makedirs(OUTDIR, exist_ok=True)

FB = r"C:\Windows\Fonts\msyhbd.ttc"
FR = r"C:\Windows\Fonts\msyh.ttc"
def f(p, s): return ImageFont.truetype(p, s)

INK = (43, 43, 43)
MUTE = (120, 116, 108)
PAPER = (247, 242, 232)
RULE = (214, 208, 196)
BOARD = "#85B7EB"          # 雾蓝：色条/序号
PILL_BG = (250, 236, 231)  # B 暖橙底
PILL_INK = (168, 85, 31)   # B 暖橙字

BOARD_MAP = {}
for a, b, name in [(1,5,"看清问题"),(6,11,"机制与需求"),(12,17,"先救身体"),
                   (18,23,"关系与约定"),(24,28,"安全与边界"),(29,31,"交还选择权")]:
    for i in range(a, b+1):
        BOARD_MAP[f"{i:02d}"] = name
ROLE = {"00": "先导", "32": "收尾"}

def tw(d, s, fp):
    b = d.textbbox((0, 0), s, font=fp)
    return b[2] - b[0]

def clean(s):
    return re.sub(r"\*\*", "", s).strip()

def split_main(text):
    """主标按标点/意群分两行；去板块前缀。"""
    text = re.sub(r"^[^·]+·\s*", "", text)  # 去「板块 · 」前缀
    for sep in ["，", "？"]:
        if sep in text:
            i = text.index(sep) + 1
            return [text[:i], text[i:]]
    # 无标点则按字数中点断
    if len(text) > 9:
        mid = len(text) // 2
        return [text[:mid], text[mid:]]
    return [text]

def build(no, board, main_lines, sub, out):
    W, H = 1080, 1440
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 20], fill=BOARD)

    # 左上：孩子与手机--板块(加粗)；00/32 用「孩子与手机 · 先导/收尾」
    x = 56
    d.text((x, 66), "孩子与手机", font=f(FR, 34), fill=MUTE)
    x += tw(d, "孩子与手机", f(FR, 34))
    if board:
        d.text((x, 66), "--", font=f(FR, 34), fill=MUTE)
        x += tw(d, "--", f(FR, 34))
        d.text((x, 62), board, font=f(FB, 36), fill=INK)
    else:
        role = ROLE.get(no, "")
        d.text((x, 66), f" · {role}", font=f(FR, 34), fill=MUTE)

    nw_ = tw(d, no, f(FB, 50))
    d.text((W - 56 - nw_, 52), no, font=f(FB, 50), fill=BOARD)
    d.line([56, 132, W - 56, 132], fill=RULE, width=2)

    n = len(main_lines)
    size = 96 if n <= 2 else 78
    while size > 54:
        f_try = f(FB, size)
        if max(tw(d, ln, f_try) for ln in main_lines) <= 920:
            break
        size -= 4
    f_main = f(FB, size)
    lh = int(size * 1.22)
    y = 320
    for ln in main_lines:
        lw = tw(d, ln, f_main)
        d.text(((W - lw) // 2, y), ln, font=f_main, fill=INK)
        y += lh

    f_sub = f(FB, 44)
    px_, py_ = 38, 18
    sw = tw(d, sub, f_sub)
    bw_, bh_ = sw + px_ * 2, 44 + py_ * 2 - 14
    bx, by = (W - bw_) // 2, y + 24
    d.rounded_rectangle([bx, by, bx + bw_, by + bh_], radius=bh_ // 2, fill=PILL_BG)
    d.text((bx + px_, by + py_ - 7), sub, font=f_sub, fill=PILL_INK)

    img.save(out, "PNG")
    return os.path.basename(out)

count = 0
for d in sorted(glob.glob(os.path.join(ROOT, "[0-9][0-9]_*"))):
    no = os.path.basename(d)[:2]
    mds = [x for x in glob.glob(os.path.join(d, "视频号文案_*.md")) if "_长视频" not in x]
    if not mds:
        continue
    t = open(mds[0], encoding="utf-8").read()
    m = re.search(r"###\s*封面\s*\n\s*-\s*大字：\*\*([^*]+)\*\*", t)
    cover = clean(m.group(1)) if m else ""
    p = re.search(r"###\s*金句大字卡[^\n]*\n\s*1\.\s*「([^」]+)」", t)
    sub = p.group(1).strip() if p else ""
    sub = re.sub(r"[。？！，、：；]", "", sub)  # 副标去标点
    if not cover or not sub:
        print(f"[跳] {no} 缺封面或金句"); continue
    main_lines = split_main(cover)
    tag = BOARD_MAP.get(no, "") or ROLE.get(no, "")
    out = os.path.join(OUTDIR, f"封面样式_{no}_{tag}.png")
    build(no, BOARD_MAP.get(no, ""), main_lines, sub, out)
    print(f"[{no}] {'/'.join(main_lines)} ｜ 副标:{sub}")
    count += 1
print("DONE", count)
