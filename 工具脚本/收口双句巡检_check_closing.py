# -*- coding: utf-8 -*-
"""
收口双句巡检 —— 检查文末「身份自述 + 认知转折」是否在位

背景（2026-09-16 用户明确）
    曾为执行"打破模板感"，把文末这两句当"可选零件"删掉，
    致 140 篇正式正文里 33 篇缺失。
    用户指出："内容很契合公众号主题，不要为了过度去模板化而省略。"

规则
    去模板化 = 换表达 ≠ 删该层。
    「身份自述」（我也是个还在重启的爸爸…）与「认知转折」（我后来…）
    是账号锚点级内容，必须保留；只轮换表达。

检出三类问题
    ① 缺身份自述   ② 缺认知转折   ③ 相邻篇句式重复

用法
    python 工具脚本/收口双句巡检_check_closing.py <系列目录>            # 如 "青春期30讲/公众号文章"
    python 工具脚本/收口双句巡检_check_closing.py <系列目录> --fix-hint  # 附改写提示
    python 工具脚本/收口双句巡检_check_closing.py --all                  # 扫全工作区
"""
import io
import os
import re
import sys
import argparse

# ---------- 自述句 / 转折句 判定 ----------
ID_HINT = ['重启', '还在学', '学着', '不是专家', '不是教育专家',
           '同路人', '也在学', '陪着', '也在练', '没什么高招']

# 认知转折句，分两档判定：
#   强档 = 有"我的认知变化"（转折标记 + 认知动词）——最理想
#   弱档 = 有"认知对照"（不是A，是B / 原来…其实… / 看下来才信…）——也认，但报告里标"弱"
COG_MARK = [r'我后来', r'后来才', r'我这才', r'我渐渐', r'我越来越',
            r'我慢慢才', r'我总算', r'我算是', r'直到.{0,8}才', r'我那时才',
            r'我才明白', r'我才信', r'我这才懂', r'后来我才', r'我才发现',
            r'我算明白了', r'我慢慢懂得', r'我后来想',
            # 2026-09-16 扩充：补写中出现的合理变体
            r'慢慢地我才', r'看下来我才', r'看完.{0,6}我才', r'试过才知道',
            r'我这才知道', r'我这才懂得', r'我才看懂', r'我才知道',
            r'我更信了', r'我也慢慢信了', r'我慢慢信了', r'我才愣住',
            r'我才醒', r'才认下', r'我才读懂', r'我懂得太晚', r'我才没再']
COG_OBJ = ['明白', '想通', '想明白', '信', '懂', '意识到', '发现', '看清',
           '才知', '才知道', '学会', '悟', '算清', '知道', '清楚',
           '看懂', '读懂', '愣住', '醒', '认下', '转弯', '打了很久']
# 弱档：认知对照句式（无"我"，但仍是认知落点）
COG_WEAK = re.compile(r'不是.{1,24}[，,].{0,6}(是|而是)|原来.{2,20}(其实|不过)|'
                      r'(从来|本来)不是.{1,20}是|与其说.{1,20}不如说|'
                      r'[，,——].{0,4}(我|我们).{0,6}(才|总算是|总算|才真的|才终于)|'
                      r'(我才醒|我才懂|我才信|才认下|才想通|才明白)|'
                      r'(摔过|错过|用过很久|花了很长时间|学得很慢|有点晚|有点难为情)')
# 收束式结论（无"我"但仍是本篇的认知落点，弱认可）
COG_CONCL = re.compile(r'(不一定|未必|其实|说到底|归根到底|真正的.{0,10}(是|不是)|'
                       r'重要的不是.{1,20}是|拼的不是.{1,16}是|'
                       r'越.{2,10}越|不是.{1,20}[，,].{0,4}(就|才)是)')

SKIP_DIR = ('_备份', '_档案', '_资产', '_专家', '工具脚本', '_归档',
            '_过程文件', '_预览', '_封面候选', '_原始', '_backup', '_tmp',
            '样板_', '正文稿_', '.git', '.workbuddy')


def read_lines(path):
    """返回 (段落列表, 全文HTML)

    ⚠️ 关键：不能按 '\\n' 切分——部分篇目是「单行压缩 HTML」（全文无换行），
    按换行切会得到 1 段、导致整篇被误判为"全缺"。
    正确做法：先按块级闭合标签切分，再剥标签。
    """
    s = io.open(path, encoding='utf-8').read()
    b = re.search(r'<body[^>]*>(.*?)</body>', s, re.S)
    t = b.group(1) if b else s
    # 按块级闭合标签 / <br> 切分，兼容"单行压缩 HTML"
    t = re.sub(r'</p>|</section>|<br\s*/?>|</div>|</h\d>', '\n', t)
    t = re.sub(r'<[^>]+>', '', t)
    t = t.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&quot;', '"')
    return [x.strip() for x in t.split('\n') if x.strip()], s


def strip_source(ls):
    """去掉来源声明行（很长、且含"文中家庭场景"等词会干扰）"""
    return [x for x in ls
            if not x.startswith('来源声明')
            and not x.startswith('【来源声明】')
            and '本文为读书笔记' not in x[:12]
            and '内容依据' not in x[:8]]


def find_id(ls, tail=12):
    """在文末找身份自述句"""
    scope = strip_source(ls)[-tail:] if len(strip_source(ls)) >= tail else strip_source(ls)
    for x in scope:
        if ('爸爸' in x or '父亲' in x) and any(h in x for h in ID_HINT):
            return x
    return None


def find_cog(ls):
    """返回 (句子, 强度) —— 强度 'strong' | 'weak' | None。

    ⚠️ 判定分两档，避免"误报一片"：
      strong = 有"我的认知变化"（转折标记 + 认知动词）——最理想
      weak   = 有"认知落点"（认知对照句 / 收束式结论）
              也认可，但报告标"弱"，供人工判断是否需升级为 strong。
    """
    scope = strip_source(ls)[-6:]
    # 强档
    for x in scope:
        if 10 < len(x) <= 80:
            if any(re.search(m, x) for m in COG_MARK) and any(o in x for o in COG_OBJ):
                return x, 'strong'
    # 弱档：认知对照 或 收束式结论
    for x in scope:
        if 8 < len(x) <= 80:
            if COG_WEAK.search(x) or COG_CONCL.search(x):
                return x, 'weak'
    return None, None


def collect(root):
    out = []
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if not any(s in d for s in SKIP_DIR)]
        for f in files:
            if f.startswith('正文_') and f.endswith('.html'):
                if any(s in dirpath for s in SKIP_DIR):
                    continue
                out.append(os.path.join(dirpath, f))
    return sorted(out)


def series_name(path):
    """从正文路径推断系列名（取 '公众号文章' 的上一级）"""
    parts = path.replace('\\', '/').split('/')
    if '公众号文章' in parts:
        i = parts.index('公众号文章')
        if i > 0:
            return '/'.join(parts[max(0, i - 2):i])
    return os.path.dirname(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('target', nargs='?', help='系列目录，如 "青春期30讲/公众号文章"')
    ap.add_argument('--all', action='store_true', help='扫全工作区')
    ap.add_argument('--fix-hint', action='store_true', help='附改写提示')
    args = ap.parse_args()

    root = args.target if args.target else os.getcwd()
    if not os.path.isdir(root):
        print('❌ 目录不存在：%s' % root)
        sys.exit(1)

    files = collect(root)
    if not files:
        print('⚠️ 未找到正文 HTML（该目录下没有 正文_*.html）')
        return

    rows = []
    for p in files:
        ls, _ = read_lines(p)
        rows.append({
            'path': p,
            'series': series_name(p),
            'name': os.path.basename(p).replace('正文_', '').replace('.html', ''),
            'id': find_id(ls),
            'cog': find_cog(ls)[0],
            'cog_lv': find_cog(ls)[1],
        })

    miss_id = [r for r in rows if not r['id']]
    miss_cog = [r for r in rows if not r['cog']]
    weak_cog = [r for r in rows if r.get('cog_lv') == 'weak']

    # 相邻篇句式重复：同一句式前后两篇都用
    def style(r):
        c = r['cog'] or ''
        for m in ['后来才', '我这才', '我后来', '我渐渐', '越来越', '直到']:
            if m in c:
                return m
        return c[:4]
    dup = []
    for a, b in zip(rows, rows[1:]):
        same_series = a['series'] == b['series']
        if same_series and a['cog'] and b['cog'] and style(a) == style(b):
            dup.append((a, b))

    print('=' * 74)
    print('收口双句巡检 · 共 %d 篇' % len(rows))
    print('=' * 74)
    print('  ❌ 缺「身份自述」 %d 篇' % len(miss_id))
    print('  ❌ 缺「认知转折」 %d 篇' % len(miss_cog))
    print('  ⚠️  相邻篇句式重复 %d 组' % len(dup))
    if weak_cog:
        print('  ⚪ 「认知转折」为弱档 %d 篇（有认知落点但非"我的转变"句式，建议人工看是否升级）' % len(weak_cog))
    print()

    def show(title, items, key):
        if not items:
            return
        print('─' * 74)
        print(title)
        print('─' * 74)
        cur = None
        for r in items:
            if r['series'] != cur:
                cur = r['series']
                print('  【%s】' % cur)
            print('     ✗ %s' % r['name'][:66])
            if args.fix_hint:
                hint = {
                    'id': '    → 补一句：我也是个还在重启的爸爸，<本篇主题对应的我犯过的错>。',
                    'cog': '    → 补一句：我后来才明白，<本篇最想留给读者的那个认知>。',
                }[key]
                print(hint)
        print()

    show('① 缺「身份自述」（我也是个还在重启的爸爸…）', miss_id, 'id')
    show('② 缺「认知转折」（我后来才明白…）', miss_cog, 'cog')

    if dup:
        print('─' * 74)
        print('③ 相邻篇句式重复（应轮换转折句式）')
        print('─' * 74)
        for a, b in dup:
            print('  ⚠️ %s' % a['name'][:52])
            print('     ↕ 与下篇同用「%s…」' % style(a))
            print('     %s' % b['name'][:52])
        print()

    total = len(miss_id) + len(miss_cog) + len(dup)
    if total == 0:
        print('✅ 全部通过：收口双句在位、相邻篇句式未重复')
    else:
        print('=' * 74)
        print('结论：需修 %d 项 ｜ 缺自述 %d ｜ 缺转折 %d ｜ 句式重复 %d 组'
              % (total, len(miss_id), len(miss_cog), len(dup)))
        print('提示：去模板化＝换表达，不等于删该层；这两句是账号锚点级内容。')
        print('=' * 74)


if __name__ == '__main__':
    main()
