# -*- coding: utf-8 -*-
"""卡片文章 · 文字排版引擎 v2（内容更完整版）
第14篇《我变了，孩子为什么还没变？》—— 共 8 张

v2 相对 v1 的三处改进（针对"文字少、没头没脑"）：
  1. 每张内容卡增加「主题标签行」——读者一眼知道这张在讲什么、讲到第几步
  2. 正文承载「相对完整的内容」——单卡可独立读懂，不再只有一句金句
  3. 张数由 5 张扩至 8 张（封面1 + 内容6 + 收尾1），承载长文主线全过程

排版引擎四条纪律（防重叠 / 防出界 / 防缺字）：
  ① 只用一种绘制方式：所有文字经统一出口
  ② 先算后画：先算总高 → 定位 → 再逐块绘制，不用绝对 y 硬写
  ③ 行首禁则：标点不出现在行首
  ④ 渲染后自检：越界 + 重叠断言（容器框只查越界）

底图策略：封面卡/收尾卡复用已生成的 AI 底图（不额外消耗积分）；
          内容卡用纯色底（零成本，且更适合承载密集文字）。
"""
import os, sys
from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding='utf-8')

# ---------- 规格 ----------
W, H = 1242, 1656
MARGIN = 96

# ---------- 三季配色（第三季 · 给信心 · 暖金棕）----------
MAIN  = '#c0924f'
DEEP  = '#a47a3a'
BAND  = '#ecdfc6'
BG    = '#fdf6ef'
INK   = '#33302b'
BROWN = '#5c3a1e'
GREY  = '#9a8f82'
LIGHT = '#f6ecd6'
PAPER = '#f2ede6'
DIM   = '#8a8078'
CREAM = '#f5ecdc'

F_TITLE = r'C:\Windows\Fonts\msyhbd.ttc'
F_REG   = r'C:\Windows\Fonts\msyh.ttc'

BASE = r'D:\个人资料\家庭教育\青春期30讲\公众号文章\卡片文章'
OUT = os.path.join(BASE, '发布包_第14篇_持久战')
BG_DIR = os.path.join(BASE, '_过程文件', '底图成品')
# ⚠️ 2026-09-19：建目录移出模块顶层（原写法让"任何 import"都凭空建目录，
#   且 OUT 是第1篇的硬编码默认值 → 跑后续篇目时可能错写进第1篇）。
#   统一交给 main() 读配置之后执行（文件末尾已有 os.makedirs(OUT, exist_ok=True)）。
_fc = {}
def font(size, bold=False):
    k = (size, bold)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(F_TITLE if bold else F_REG, size)
    return _fc[k]

BOXES = []        # 文字块（参与越界 + 重叠检测）
CONTAINERS = []   # 容器框（只参与越界检测）

NOTES = ['课程学习心得 · 家庭场景改编', '青春期30讲 · 第14篇　第三季 · 给信心']  # [0]=改编标注(P0) [1]=系列行
NO_HEAD = set('。，、；：！？）》”’%…·')


def wrap(draw, text, f, max_w):
    """按像素宽度断行；含行首禁则"""
    lines, cur = [], ''
    for ch in text:
        if ch == '\n':
            lines.append(cur); cur = ''; continue
        if draw.textlength(cur + ch, font=f) <= max_w:
            cur += ch
        else:
            if ch in NO_HEAD and cur:
                cur += ch
            else:
                lines.append(cur); cur = ch
    if cur:
        lines.append(cur)
    return lines


def para_h(draw, paras, f, max_w, lh=1.78):
    tot = 0
    for i, p in enumerate(paras):
        n = len(wrap(draw, p, f, max_w))
        tot += int(f.size * lh) * n
        if i < len(paras) - 1:
            tot += int(f.size * 0.62)
    return tot


def draw_paras(draw, paras, x, y, f, color, max_w, lh=1.78):
    step = int(f.size * lh)
    for i, p in enumerate(paras):
        for ln in wrap(draw, p, f, max_w):
            draw.text((x, y), ln, font=f, fill=color)
            BOXES.append((x, y, x + draw.textlength(ln, font=f), y + f.size))
            y += step
        if i < len(paras) - 1:
            y += int(f.size * 0.62)
    return y


def layout_center_lines(draw, items, lh_ratio=1.36, gap=None, pad_x=18):
    """⭐ 居中多行排版（可含高亮块）—— 先算后画。

    ⛔ 实测教训（2026-09-15）：旧写法 `by1 = y - 12 + f.size + 24` 是拿 size 估算块高，
       但**微软雅黑的实际墨迹高度比 size 大**（含下伸部：点/钩/撇捺）。
       实测：size 126 → 墨迹底在 y+152，块底只到 y+138 → **文字下缘超出块底 14px**
       （"点"的四点底、"子"的钩被色块切掉；第14篇封面、第14/15篇收尾卡均中招）。

    ✅ 正确做法：
       ① 用 draw.textbbox 量**该行文字的真实墨迹**，按墨迹上/下各留 py 定块高 → 块永远完整包住文字；
       ② 预计算每行的 y，保证**块不与相邻行的墨迹重叠**（否则块会吞掉上一行文字的脚）。

    items: [{'t': 文本, 'f': font, 'c': 文字色, 'hl': 高亮底色 or None}]
    返回 (lines, total_h)；lines 内每项含 x/y/box，供绘制与自检复用。
    """
    INF = []
    for it in items:
        f = it['f']
        bb = draw.textbbox((0, 0), it['t'], font=f)
        hl = it.get('hl')
        py = max(10, int(f.size * 0.16)) if hl else 0   # 块内边距按字号自适应
        INF.append({'it': it, 'f': f,
                    'ink_top': bb[1], 'ink_bot': bb[3], 'py': py})

    if not INF:
        return [], 0
    if gap is None:
        gap = max(12, int(INF[0]['f'].size * 0.12))

    ys = [0.0]
    for i in range(len(INF) - 1):
        cur, nxt = INF[i], INF[i + 1]
        base = ys[i] + int(cur['f'].size * lh_ratio)     # 常规行距下限
        # 让相邻行的「块/墨迹」互不覆盖：取两侧 padding 的较大者
        need = (ys[i] + cur['ink_bot'] + gap - nxt['ink_top']
                + max(cur['py'], nxt['py']))
        ys.append(max(base, need))

    last = INF[-1]
    total = ys[-1] + last['ink_bot'] + last['py']

    out = []
    for i, m in enumerate(INF):
        f, t = m['f'], m['it']['t']
        tw = draw.textlength(t, font=f)
        x = (W - tw) / 2
        y = ys[i]
        box = None
        if m['it'].get('hl'):
            box = (x - pad_x, y + m['ink_top'] - m['py'],
                   x + tw + pad_x, y + m['ink_bot'] + m['py'])
            # ⛔ 硬断言：色块必须完整包住该行文字的真实墨迹
            #    （否则"点"的四点底、"子"的钩等下伸笔画会被色块切掉）
            assert box[1] <= y + m['ink_top'] and box[3] >= y + m['ink_bot'], \
                '高亮块未包住文字墨迹：%r' % t
        out.append({'t': t, 'f': f, 'c': m['it']['c'], 'hl': m['it'].get('hl'),
                    'x': x, 'y': y, 'box': box})
    return out, total


def draw_center_lines(draw, lines):
    """按 layout_center_lines 的结果绘制（块先画、字后画）"""
    for L in lines:
        if L['box']:
            draw.rounded_rectangle(list(L['box']), radius=14, fill=L['hl'])
            draw.text((L['x'], L['y']), L['t'], font=L['f'], fill=L.get('tc', '#2a2016'))
            BOXES.append(L['box'])
        else:
            draw.text((L['x'], L['y']), L['t'], font=L['f'], fill=L['c'])
            BOXES.append((L['x'], L['y'],
                          L['x'] + draw.textlength(L['t'], font=L['f']),
                          L['y'] + L['f'].size))


def top_labels(draw, light=False):
    f = font(26)
    t = NOTES[1] if len(NOTES) > 1 else NOTES[0]
    y = 34
    tw = draw.textlength(t, font=f)
    draw.text(((W - tw) / 2, y), t, font=f, fill='#e9dcc6' if light else '#b8ac9c')
    BOXES.append(((W - tw) / 2, y, (W + tw) / 2, y + f.size))
    f2 = font(25)
    tw2 = draw.textlength(NOTES[0], font=f2)
    y2 = y + f.size + 12
    draw.text(((W - tw2) / 2, y2), NOTES[0], font=f2, fill='#ded0b8' if light else '#b8ac9c')
    BOXES.append(((W - tw2) / 2, y2, (W + tw2) / 2, y2 + f2.size))


def sig(draw, light=False):
    f = font(28)
    t = '归途有光 · 和孩子一起重启'
    tw = draw.textlength(t, font=f)
    y = H - MARGIN
    draw.text(((W - tw) / 2, y), t, font=f, fill=CREAM if light else GREY)
    BOXES.append(((W - tw) / 2, y, (W + tw) / 2, y + f.size))


def fit_bg(name):
    im = Image.open(os.path.join(BG_DIR, name)).convert('RGB')
    if im.size != (W, H):
        im = im.resize((W, H), Image.LANCZOS)
    return im


# ============================================================
# 内容卡：主题标签 + 主标题 + 细线 + 正文段落 + 左侧竖条
# ============================================================
def content_card(topic, head, paras):
    im = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(im)
    top_labels(d)

    X = MARGIN + 52
    MW = W - X - MARGIN
    sc = CFG.get('content_scale', 1.0)
    f_topic = font(int(32 * sc))
    f_head  = font(int(60 * sc), True)
    f_body  = font(int(40 * sc))

    head_lines = wrap(d, head, f_head, MW)
    head_h = int(f_head.size * 1.34) * len(head_lines)

    body_h = para_h(d, paras, f_body, MW)
    total = f_topic.size + 28 + head_h + 40 + 30 + body_h

    # 可用区：上避开顶部两行标注，下避开署名
    AREA_TOP, AREA_BOT = 132, H - MARGIN - 26
    y = AREA_TOP + max(0, (AREA_BOT - AREA_TOP - total) * 0.50)
    top = y

    # 主题标签
    d.text((X, y), topic, font=f_topic, fill=MAIN)
    BOXES.append((X, y, X + d.textlength(topic, font=f_topic), y + f_topic.size))
    y += f_topic.size + 28

    # 主标题
    for ln in head_lines:
        d.text((X, y), ln, font=f_head, fill=DEEP)
        BOXES.append((X, y, X + d.textlength(ln, font=f_head), y + f_head.size))
        y += int(f_head.size * 1.34)
    y += 40

    # 细线
    d.rounded_rectangle([X, y, X + 88, y + 4], radius=2, fill=BAND)
    y += 30

    # 正文
    draw_paras(d, paras, X, y, f_body, BROWN, MW)

    # 左侧竖条（跟随内容）
    d.rounded_rectangle([MARGIN + 12, top - 4, MARGIN + 19, top + total - 24],
                        radius=4, fill=MAIN)
    sig(d)
    return im


# ============================================================
# 对照卡
# ============================================================
def compare_card(topic, rows):
    im = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(im)
    top_labels(d)
    X = MARGIN + 52
    f_topic = font(32)
    f_h = font(56, True)
    f_b = font(40)

    pad, PADIN = MARGIN, 48
    heights = []
    for _, title, body in rows:
        n = len(wrap(d, body, f_b, W - pad * 2 - PADIN * 2))
        heights.append(PADIN * 2 + f_h.size + 30 + int(f_b.size * 1.78) * n)
    gap = 44
    total = f_topic.size + 28 + sum(heights) + gap * (len(rows) - 1)

    AREA_TOP, AREA_BOT = 132, H - MARGIN - 26
    y = AREA_TOP + max(0, (AREA_BOT - AREA_TOP - total) * 0.50)
    top = y
    d.text((X, y), topic, font=f_topic, fill=MAIN)
    BOXES.append((X, y, X + d.textlength(topic, font=f_topic), y + f_topic.size))
    y += f_topic.size + 28

    for (bgc, title, body), bh in zip(rows, heights):
        d.rounded_rectangle([pad, y, W - pad, y + bh], radius=24, fill=bgc)
        CONTAINERS.append((pad, y, W - pad, y + bh))
        d.text((pad + PADIN, y + PADIN), title, font=f_h, fill=DEEP if bgc == LIGHT else DIM)
        BOXES.append((pad + PADIN, y + PADIN,
                      pad + PADIN + d.textlength(title, font=f_h), y + PADIN + f_h.size))
        by = y + PADIN + f_h.size + 30
        col = BROWN if bgc == LIGHT else '#6b625a'
        for ln in wrap(d, body, f_b, W - pad * 2 - PADIN * 2):
            d.text((pad + PADIN, by), ln, font=f_b, fill=col)
            BOXES.append((pad + PADIN, by,
                          pad + PADIN + d.textlength(ln, font=f_b), by + f_b.size))
            by += int(f_b.size * 1.78)
        y += bh + gap

    sig(d)
    return im


# ============================================================
# 时间线卡
# ============================================================
def timeline_card(topic, head, nodes):
    im = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(im)
    top_labels(d)
    X = MARGIN + 82
    MW = W - X - MARGIN

    f_topic = font(32)
    f_head  = font(54, True)
    f_t     = font(50, True)
    f_b     = font(38)

    head_lines = wrap(d, head, f_head, MW)

    # 先量总高（用于垂直居中）
    _h = f_topic.size + 24 + int(f_head.size * 1.34) * len(head_lines) + 50
    for _t, _body in nodes:
        _h += f_t.size + 20 + int(f_b.size * 1.76) * len(wrap(d, _body, f_b, MW)) + 52
    total = _h - 52

    AREA_TOP, AREA_BOT = 132, H - MARGIN - 26
    y = AREA_TOP + max(0, (AREA_BOT - AREA_TOP - total) * 0.50)
    top = y
    d.text((X - 30, y), topic, font=f_topic, fill=MAIN)
    BOXES.append((X - 30, y, X - 30 + d.textlength(topic, font=f_topic), y + f_topic.size))
    y += f_topic.size + 24
    for ln in head_lines:
        d.text((X - 30, y), ln, font=f_head, fill=DEEP)
        BOXES.append((X - 30, y, X - 30 + d.textlength(ln, font=f_head), y + f_head.size))
        y += int(f_head.size * 1.34)
    y += 50

    line_top = y + 24
    for t, body in nodes:
        d.ellipse([MARGIN + 6, y + 20, MARGIN + 37, y + 51], fill=MAIN)
        BOXES.append((MARGIN + 6, y + 20, MARGIN + 37, y + 51))
        d.text((X, y), t, font=f_t, fill=DEEP)
        BOXES.append((X, y, X + d.textlength(t, font=f_t), y + f_t.size))
        yy = y + f_t.size + 20
        for ln in wrap(d, body, f_b, MW):
            d.text((X, yy), ln, font=f_b, fill=BROWN)
            BOXES.append((X, yy, X + d.textlength(ln, font=f_b), yy + f_b.size))
            yy += int(f_b.size * 1.76)
        y = yy + 52
    d.rounded_rectangle([MARGIN + 17, line_top, MARGIN + 24, y - 52 - 8], radius=3, fill=BAND)
    sig(d)
    return im


# ============================================================
# 封面卡 / 收尾卡
# ============================================================
def cover_card():
    """封面卡（抓眼球）
    ⚠️ 贴图封面按 16:9 中心裁切展示 —— 核心文案必须落在 y 479~1177 安全区内。
    文案从 CFG['cover'] 读入：{'lines':[{'t':..,'hl':bool},..], 'size':126}

    ⭐ 版式纪律（2026-09-15 修）：用 layout_center_lines「先算后画」——
       高亮块按**文字墨迹实测**包住文字，不再用 size 估算
       （旧版按 size 估块高，导致"点""子"等下伸笔画被色块切掉）。
    """
    cfg = CFG.get('cover', {})
    lns = cfg.get('lines') or [{'t': '我忍了20天'}, {'t': '没吼他'}, {'t': '他一点没变', 'hl': True}]
    fsize = int(cfg.get('size', 126))

    im = soften_bg(fit_bg(cfg.get('bg', '封面卡_底图.png')),
                   blur=cfg.get('blur', 1.8), veil=cfg.get('veil', 0.26),
                   top=cfg.get('top', 0.34), bottom=cfg.get('bottom', 0.18))
    d = ImageDraw.Draw(im)

    SAFE_16_9 = (479, 1177)
    items = [{'t': l['t'], 'f': font(fsize, True),
              'c': '#2a2016' if l.get('hl') else CREAM,
              'hl': '#e8c98a' if l.get('hl') else None} for l in lns]

    f_note = font(28)
    n_line_cnt = 1 + (1 if len(NOTES) > 1 else 0)
    note_h = n_line_cnt * (f_note.size + 8)

    LINES, total = layout_center_lines(d, items)
    pad_top, pad_bot = 44, 44
    avail = SAFE_16_9[1] - SAFE_16_9[0] - total - pad_top - pad_bot - note_h
    if avail < 0:
        raise SystemExit('❌ 封面卡内容超出 16:9 安全区 %.0fpx，请减小字号或减少行数' % -avail)
    y0 = SAFE_16_9[0] + pad_top + note_h + avail / 2

    # 顶部两行（系列行 + 改编标注）——必须在 16:9 安全区内
    ny = y0 - note_h + 4
    if len(NOTES) > 1:
        t1 = NOTES[1]
        tw1 = d.textlength(t1, font=f_note)
        if ny >= SAFE_16_9[0]:
            d.text(((W - tw1) / 2, ny), t1, font=f_note, fill='#c9bda8')
            BOXES.append(((W - tw1) / 2, ny, (W + tw1) / 2, ny + f_note.size))
        ny += f_note.size + 8
    note = NOTES[0]
    tw = d.textlength(note, font=f_note)
    d.text(((W - tw) / 2, ny), note, font=f_note, fill='#e2d3b8')
    BOXES.append(((W - tw) / 2, ny, (W + tw) / 2, ny + f_note.size))

    # 正文各行（含高亮块）——平移到 y0
    for L in LINES:
        L['y'] += y0
        if L['box']:
            bx0, by0, bx1, by1 = L['box']
            L['box'] = (bx0, by0 + y0, bx1, by1 + y0)
    draw_center_lines(d, LINES)

    f_s = font(28)
    t_s = '归途有光 · 和孩子一起重启'
    tw_s = d.textlength(t_s, font=f_s)
    sy = y0 + total + 18
    d.text(((W - tw_s) / 2, sy), t_s, font=f_s, fill=CREAM)
    BOXES.append(((W - tw_s) / 2, sy, (W + tw_s) / 2, sy + f_s.size))
    return im


def soften_bg(im, blur=2.6, veil=0.34, veil_color='#1a1310', top=0.46, bottom=0.42):
    """底图重处理：强柔化 + 整体压暗 + 上下渐暗
    用途：收尾卡文字量大，需腾出 JPEG 压缩空间并保证文字可读"""
    from PIL import ImageFilter
    im = im.filter(ImageFilter.GaussianBlur(blur))
    v = Image.new('RGB', im.size, veil_color)
    im = Image.blend(im, v, veil)
    W_, H_ = im.size
    m = Image.new('L', (1, H_), 0)
    px = m.load()
    end_t = int(H_ * 0.42)
    start_b = int(H_ * 0.50)
    for y in range(H_):
        vv = 0
        if y < end_t:
            vv = int(255 * top * (1 - y / end_t) ** 0.8)
        elif y > start_b:
            t = (y - start_b) / (H_ - start_b)
            vv = int(255 * bottom * (t ** 0.9))
        px[0, y] = vv
    return Image.composite(Image.new('RGB', im.size, veil_color), im, m.resize((W_, H_)))


def closing_card():
    """收尾卡：场景承接 + 落点金句
    文案从 CFG['closing'] 读入：{'scene':[...], 'quote':[{'t':..,'hl':bool},..], 'size':42,'qsize':78}

    ⭐ 版式纪律（2026-09-15 修）：落点金句的高亮块同样走 layout_center_lines 墨迹实测，
       不再用 size 估算（旧版把"够"字的下伸笔画切掉）。
    """
    cfg = CFG.get('closing', {})
    scene = cfg.get('scene') or []
    quote = cfg.get('quote') or [{'t': '孩子没变，不是白忍了。'},
                                 {'t': '是汤刚调好，萝卜还没泡够。', 'hl': True}]
    fsize = int(cfg.get('size', 42))
    qsize = int(cfg.get('qsize', 78))

    im = soften_bg(fit_bg(cfg.get('bg', '收尾卡_底图.png')),
                   blur=cfg.get('blur', 4.2), veil=cfg.get('veil', 0.44),
                   top=cfg.get('top', 0.50), bottom=cfg.get('bottom', 0.48))
    d = ImageDraw.Draw(im)
    top_labels(d, light=True)
    X = MARGIN + 46
    MW = W - X - MARGIN

    f_b = font(fsize)
    y = int(cfg.get('y0', 158))
    if scene:
        y = draw_paras(d, scene, X, y, f_b, CREAM, MW, 1.74) + 52

    f_j = font(qsize, True)
    items = [{'t': q['t'], 'f': f_j,
              'c': '#2a2016' if q.get('hl') else CREAM,
              'hl': '#e8c98a' if q.get('hl') else None} for q in quote]
    LINES, total = layout_center_lines(d, items, lh_ratio=1.46)

    AREA_BOT = H - MARGIN - 26
    if y + total > AREA_BOT:
        # 空间不足：整体上移（但不越过顶部两行标注）
        y = max(140, AREA_BOT - total)

    for L in LINES:
        L['y'] += y
        if L['box']:
            bx0, by0, bx1, by1 = L['box']
            L['box'] = (bx0, by0 + y, bx1, by1 + y)
    draw_center_lines(d, LINES)

    sig(d, light=True)
    return im


# ============================================================
# 自检
# ============================================================
def check_16_9(label, boxes):
    """贴图封面按 16:9 中心裁切展示：检查文字是否全部落在裁切带内。
    仅对首图（封面卡）强制；其余卡不裁切，故只报告。"""
    y0, y1 = int((H - W * 9 / 16) / 2), int((H + W * 9 / 16) / 2)
    out = []
    for b in boxes:
        if b[1] < y0 or b[3] > y1:
            out.append('出16:9安全区 %s' % (tuple(round(v) for v in b),))
    return out, (y0, y1)


def check(min_pad=14):
    bad = []
    for b in list(BOXES) + list(CONTAINERS):
        if b[0] < min_pad or b[1] < min_pad or b[2] > W - min_pad or b[3] > H - min_pad:
            bad.append('越界 %s' % (tuple(round(v) for v in b),))
    for i in range(len(BOXES)):
        for j in range(i + 1, len(BOXES)):
            a, b2 = BOXES[i], BOXES[j]
            ox = min(a[2], b2[2]) - max(a[0], b2[0])
            oy = min(a[3], b2[3]) - max(a[1], b2[1])
            if ox > 6 and oy > 6:
                bad.append('重叠 %s <-> %s' % (tuple(round(v) for v in a), tuple(round(v) for v in b2)))
    return bad


def save(im, name, limit_kb=100):
    """写入带重试：Windows 下文件可能被预览/杀毒短暂占用"""
    import time
    p = os.path.join(OUT, name)
    for q in range(93, 29, -3):
        for attempt in range(6):
            try:
                im.save(p, 'JPEG', quality=q, optimize=True, subsampling=2)
                break
            except (PermissionError, OSError):
                if attempt == 5:
                    raise
                time.sleep(0.4)
        kb = os.path.getsize(p) / 1024
        if kb <= limit_kb:
            return p, q, kb
    return p, 30, os.path.getsize(p) / 1024


# ============================================================
# 5 张卡（张数依据：多来源一致指向「2–3 张最佳、5 张以上掉量」，
#         故收敛为 5 张上限；每张内容做厚，确保单卡信息自足）
#   ⛔ 已从 8 张改为 5 张 —— 原 8 张方案与"张数越多越限流"的实测结论冲突
# ============================================================
def build_cards():
    """从 CFG['cards'] 构建卡片任务列表。
    每项：{'file':文件名, 'type':'content|compare|timeline|cover|closing', ...}
    未提供配置时回退到内置示例（第14篇）。"""
    cs = CFG.get('cards')
    if not cs:
        # 内置兜底（第14篇）
        return [
            ('第XX篇_卡片_01_封面.jpg', cover_card),
            ('第XX篇_卡片_05_收尾.jpg', closing_card),
        ]
    out = []
    for c in cs:
        t = c.get('type')
        f = c['file']
        if t == 'cover':
            out.append((f, cover_card))
        elif t == 'closing':
            out.append((f, closing_card))
        elif t == 'content':
            out.append((f, (lambda cc: (lambda: content_card(cc['topic'], cc['head'], cc['paras'])))(c)))
        elif t == 'compare':
            rows = [(LIGHT if i == 0 else PAPER, r[0], r[1]) for i, r in enumerate(c['rows'])]
            out.append((f, (lambda cc, rr: (lambda: compare_card(cc['topic'], rr)))(c, rows)))
        elif t == 'timeline':
            out.append((f, (lambda cc: (lambda: timeline_card(cc['topic'], cc['head'],
                         [(n[0], n[1]) for n in cc['nodes']])))(c)))
        else:
            raise SystemExit('未知卡片类型: %s' % t)
    return out


CARDS = []


def main():
    import argparse, json
    global BASE, OUT, BG_DIR, CFG, CARDS, NOTES
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', required=True, help='卡片内容 JSON 配置')
    ap.add_argument('--out', help='输出目录（默认 <base>/发布包_第X篇_xxx）')
    ap.add_argument('--bg', help='底图目录（默认 <base>/_过程文件/底图成品）')
    ap.add_argument('--only', help='只渲染文件名含该串的卡')
    a = ap.parse_args()

    CFG = json.load(io.open(a.config, encoding='utf-8')) if False else json.loads(
        open(a.config, encoding='utf-8').read())
    BASE = CFG.get('base', BASE)
    OUT = a.out or CFG.get('out') or OUT
    BG_DIR = a.bg or CFG.get('bg') or os.path.join(BASE, '_过程文件', '底图成品')
    if CFG.get('notes'):
        NOTES = CFG['notes']
    os.makedirs(OUT, exist_ok=True)
    CARDS = build_cards()

    print('=== 渲染（共 %d 张）===' % len(CARDS))
    results = []
    for name, fn in CARDS:
        if a.only and a.only not in name:
            continue
        BOXES.clear(); CONTAINERS.clear()
        im = fn()
        bad = check()
        if '封面' in name:
            b169, band = check_16_9(name, list(BOXES))
            if b169:
                bad += b169
        p, q, kb = save(im, name)
        if kb > 100:
            bad.append('体积超限 %.1fKB > 100KB（已压到最低 q=%d）' % (kb, q))
        st = '✅' if not bad else '❌'
        results.append((name, st, q, kb, bad))
        print('%s %-28s q=%-3d %6.1fKB' % (st, name, q, kb))
        for b in bad[:6]:
            print('     ', b)
    ok = all(r[1] == '✅' for r in results) and results
    print('\n%s' % ('全部通过 ✅' if ok else '存在问题 ❌'))


if __name__ == '__main__':
    main()
