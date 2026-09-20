# -*- coding: utf-8 -*-
"""补写收口双句 · 第二批（19 篇）

系列与篇目：
  为什么学生不喜欢上学  7 篇（跳过第 6 篇，已有）
  你是孩子最好的玩具     4 篇（第 3/4/5/6 篇）
  解码青春期            8 篇（全缺）

三个系列的尾部结构不同，用「系列级锚点策略」分别处理：
  - 为什么学生不喜欢上学 / 你是孩子最好的玩具 / 解码青春期
    统一策略：在「来源声明块」之前插入一个收口色块。

用法：
  python 工具脚本/补写收口双句_apply_closing2.py           # 试运行
  python 工具脚本/补写收口双句_apply_closing2.py --apply   # 写入
"""
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _closing_content2 import CLOSING  # noqa: E402

# 系列级配置：正文目录、收口色块配色（取自该系列既有浅色，不新增色值）
SERIES = {
    '为什么学生不喜欢上学': dict(
        root='为什么学生不喜欢上学/公众号文章',
        bg='#eef4f3', color='#3a4a47',
        anchors=['来源声明', '来源说明'],
    ),
    '你是孩子最好的玩具': dict(
        root='王金海讲书/你是孩子最好的玩具/公众号文章',
        bg='#faf3ec', color='#5a4636',
        anchors=['来源声明', '来源说明'],
    ),
    '解码青春期': dict(
        root='王金海讲书/解码青春期/公众号文章',
        bg='#f6ece2', color='#5a4636',
        anchors=['本文为读书笔记', '来源声明'],
    ),
}

# 要找的「顶层块容器」开标签（各系列统一是这个形态）
BLOCK_OPEN = '<section style="box-sizing:border-box;width:100%;display:block">'


def make_block(bg, color, id_text, cog_text):
    """生成收口色块。span 开闭严格配平（整块一个 span 包两行）。"""
    body = id_text + '<br>' + cog_text
    return (
        '  <section style="box-sizing:border-box;width:100%;display:block">'
        '<section style="box-sizing:border-box;padding:20px 30px 8px;width:100%;display:block">\n'
        '    <section style="box-sizing:border-box;background:' + bg + ';border-radius:10px;width:100%;display:block">\n'
        '      <section style="box-sizing:border-box;width:100%;display:block">'
        '<section style="box-sizing:border-box;padding:20px 22px;font-size:14.5px;line-height:1.9;'
        'text-align:center;width:100%;display:block">\n'
        '        <span style="color:' + color + '">' + body + '</span>\n'
        '      </section></section>\n'
        '    </section>\n'
        '  </section></section>\n\n'
    )


def find_insert_pos(s, anchors):
    """定位插入位置：来源声明块的**起点**（不是嵌套内层）。

    ⚠️ 踩坑记录（2026-09-16）：首版取"声明前最后一个顶层开标签"，
       结果取到了声明块**内部的嵌套 section**，收口色块被插进来源声明卡片里面。
       正确做法：优先用 `<!-- 来源声明 -->` 注释定位；没有注释时，
       从声明文字**向上数标签嵌套**，找到包住它的最外层 section。
    """
    decl = -1
    for kw in anchors:
        i = s.rfind(kw)
        if i > 0:
            decl = i
            break
    if decl < 0:
        return None, '未找到来源声明锚点'

    # ① 优先：注释标记 `<!-- 来源声明 -->`
    cm = s.rfind('<!-- 来源声明 -->', 0, decl)
    if cm > 0:
        # 注释后第一个 section 开标签即声明块起点
        m = re.search(r'<section\s', s[cm:decl])
        if m:
            pos = cm + m.start()
            return pos, 'ok·注释定位（距声明 %d）' % (decl - pos)

    # ② 回退：向上数嵌套，找到包住声明文字的最外层 section
    #    以「block 开标签」为步进，找连续开标签链的起点
    open_re = re.compile(re.escape(BLOCK_OPEN))
    hits = [m.start() for m in open_re.finditer(s[:decl])]
    if not hits:
        return None, '来源声明前无顶层块容器'
    # 从最后一个 block 开标签向前，找「连续紧邻」的链首（中间只允许有标签、无正文）
    idx = len(hits) - 1
    while idx > 0:
        prev, cur = hits[idx - 1], hits[idx]
        gap = re.sub(r'<[^>]+>', '', s[prev:cur]).strip()
        # 若两个开标签之间没有正文文字，说明 cur 是 prev 的内层 → 继续向前
        if gap == '':
            idx -= 1
        else:
            break
    pos = hits[idx]
    return pos, 'ok·嵌套回溯（距声明 %d）' % (decl - pos)


def already_done(s):
    """⚠️ 2026-09-19 修正：原判据过松——只要出现"还在重启的爸爸"就判完成，
    导致"有自述但缺认知转折"的篇目（如「改善你的亲子关系」第1、2篇）被永久跳过。
    → 改为**两项分别检查**：自述在位 **且** 转折句在位，才算完成。"""
    has_id = ('还在重启的爸爸' in s) or ('还在学着' in s and '爸爸' in s) \
             or ('还在练' in s and '爸爸' in s)
    cog_marks = ['我后来', '后来才', '我这才', '我渐渐', '我越来越', '我慢慢才',
                 '我总算', '我算是', '我才明白', '我才信', '后来我才',
                 '我才发现', '我花了很久', '我如今', '这些年我才']
    has_cog = any(m in s for m in cog_marks)
    return has_id and has_cog


def run(apply=False):
    root_base = r'D:\个人资料\家庭教育'
    ok = skip = fail = 0
    for series, cfg in SERIES.items():
        d = os.path.join(root_base, cfg['root'])
        if not os.path.isdir(d):
            print('❌ 目录不存在：%s' % d)
            continue
        print('▌ %s' % series)
        for sub in sorted([x for x in os.listdir(d) if x.startswith('发布包')]):
            fp = os.path.join(d, sub)
            if not os.path.isdir(fp):
                continue
            cands = [x for x in os.listdir(fp) if x.startswith('正文_')]
            if not cands:
                continue
            p = os.path.join(fp, cands[0])
            s = io.open(p, encoding='utf-8').read()

            c = CLOSING.get(series, {}).get(sub)
            if not c:
                print('   ⏭ %-42s 不在本次范围' % sub[:40])
                skip += 1
                continue
            if already_done(s):
                print('   ⏭ %-42s 已有收口双句' % sub[:40])
                skip += 1
                continue
            pos, why = find_insert_pos(s, cfg['anchors'])
            if pos is None:
                print('   ❌ %-42s %s' % (sub[:40], why))
                fail += 1
                continue

            blk = make_block(cfg['bg'], cfg['color'], c['full_id'], c['cog'])
            new = s[:pos] + blk + s[pos:]
            if apply:
                io.open(p, 'w', encoding='utf-8').write(new)
            print('   %s %-42s +%d 字符 ｜ %s' % ('✅' if apply else '○', sub[:40], len(new) - len(s), why))
            ok += 1
        print()
    print('=' * 64)
    print(('✅ 已写入 %d 篇' % ok if apply else '（试运行）待写 %d 篇' % ok) + ' ｜ 跳过 %d ｜ 失败 %d' % (skip, fail))


if __name__ == '__main__':
    run(apply='--apply' in sys.argv)
