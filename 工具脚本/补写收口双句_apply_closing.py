# -*- coding: utf-8 -*-
"""为「刻意练习 / 幸福的方法 / 微习惯」三系列补写收口双句（方案A · 16 篇）

只改文末：在「来源声明」块之前插入一个浅色圆角色块，内含两行——
  ① 身份自述（我也是个还在重启的爸爸 + 本篇具象的"我犯过的错"）
  ② 认知转折（本篇最想留给读者的那个认知）

不动正文主体一个字。
"""
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _closing_content import CLOSING  # noqa: E402

# 各系列收口色块配色（取自该系列既有色值，不新增色）
STYLE = {
    '刻意练习': dict(bg='#f3f7f5', color='#315f5a'),
    '幸福的方法': dict(bg='#f5ede0', color='#8d642f'),
    '微习惯': dict(bg='#f3f7f5', color='#315f5a'),
}

# 来源声明锚点关键词（按系列）
ANCHOR = {
    '刻意练习': ['内容依据'],
    '幸福的方法': ['本文参考', '本文为课程与读书'],
    '微习惯': ['内容参考'],
}

# 插入位置之前的那个 <p> 开标签必须落在这个距离内，才算"来源声明块"，否则不插
MAX_GAP = 600


def make_block(series, id_text, cog_text):
    """生成收口双句色块。

    ⚠️ span 开闭必须严格配平——整块只用一个 span 包住两行，
       否则渲染器报"配平!span+1"，交付校验不过。
    """
    st = STYLE[series]
    body = id_text + '<br>' + cog_text
    parts = [
        '  <section style="box-sizing:border-box;width:100%;display:block">'
        '<section style="box-sizing:border-box;padding:20px 30px 8px;width:100%;display:block">\n',
        '    <section style="box-sizing:border-box;background:', st['bg'], ';border-radius:10px;width:100%;display:block">\n',
        '      <section style="box-sizing:border-box;width:100%;display:block">'
        '<section style="box-sizing:border-box;padding:20px 22px;font-size:14.5px;line-height:1.9;'
        'text-align:center;width:100%;display:block">\n',
        '        <span style="color:', st['color'], '">', body, '</span>\n',
        '      </section></section>\n',
        '    </section>\n',
        '  </section></section>\n\n',
    ]
    return ''.join(parts)


def find_insert_pos(s, series):
    """返回 (位置, 说明)。位置 = 来源声明块 <p 的开头；找不到返回 (None, 原因)"""
    best = None
    for kw in ANCHOR[series]:
        i = s.rfind(kw)
        if i > 0:
            best = i
            break
    if best is None:
        return None, '未找到来源声明锚点'
    j = s.rfind('<p ', 0, best)
    if j < 0 or best - j > MAX_GAP:
        return None, '锚点前无紧邻的 <p> 块（gap=%s）' % (best - j)
    return j, 'ok'


def already_done(s):
    return ('还在重启的爸爸' in s) or ('还在学着' in s and '爸爸' in s)


def process(series, root, apply=False):
    d = os.path.join(root, '王金海讲书', series, '公众号文章')
    if not os.path.isdir(d):
        print('❌ 目录不存在：%s' % d)
        return []
    results = []
    for sub in sorted([x for x in os.listdir(d) if x.startswith('发布包')]):
        fp = os.path.join(d, sub)
        if not os.path.isdir(fp):
            continue
        cands = [x for x in os.listdir(fp) if x.startswith('正文_')]
        if not cands:
            results.append((sub, 'skip', '无正文文件'))
            continue
        p = os.path.join(fp, cands[0])
        s = io.open(p, encoding='utf-8').read()

        if already_done(s):
            results.append((sub, 'skip', '已有收口双句'))
            continue
        c = CLOSING.get(series, {}).get(sub)
        if not c:
            results.append((sub, 'skip', '无对应文案'))
            continue
        pos, why = find_insert_pos(s, series)
        if pos is None:
            results.append((sub, 'fail', why))
            continue

        blk = make_block(series, c.get('full_id', c['id']), c['cog'])
        new = s[:pos] + blk + s[pos:]
        if apply:
            io.open(p, 'w', encoding='utf-8').write(new)
        results.append((sub, 'ok' if apply else 'dry', '+%d 字符' % (len(new) - len(s))))
    return results


if __name__ == '__main__':
    apply = '--apply' in sys.argv
    root = r'D:\个人资料\家庭教育'
    total_ok = 0
    for series in ['刻意练习', '幸福的方法', '微习惯']:
        print('▌ %s' % series)
        for sub, st, msg in process(series, root, apply=apply):
            mark = {'ok': '✅', 'dry': '○', 'skip': '⏭', 'fail': '❌'}[st]
            print('   %s %-42s %s' % (mark, sub[:40], msg))
            if st == 'ok':
                total_ok += 1
        print()
    print('=' * 60)
    print(('✅ 已写入 %d 篇' % total_ok) if apply else '（试运行，未写入；加 --apply 执行）')
