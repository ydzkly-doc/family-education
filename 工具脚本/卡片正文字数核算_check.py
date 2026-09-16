# -*- coding: utf-8 -*-
"""卡片正文「后台口径」字数核算器

⭐ 后台计数口径（据实测反推，2026-09-15 用户实测校准）：
    计数字符 = 标题 + content
    其中 **换行符算 1 个字符**（CRLF 也算 1 个，不重复计 \\r）
    上限 = 1064

⛔ 历史踩坑：先前用「去掉所有空白」口径核算，**少算了 46 个换行符**，
   报出 983 而真实为 1035（用户后台看到的数字），导致超出限制而不自知。

用法：
  python 卡片正文字数核算_check.py <正文txt> --title "标题" [--limit 1064] [--target 950]
"""
import sys, os, io, argparse


def count_backend(text):
    """按后台口径计数：CRLF 归一为单个换行，全部字符计入（含换行、空格、标点）"""
    norm = text.replace('\r\n', '\n').replace('\r', '\n')
    return len(norm.rstrip('\n')), norm


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('path')
    ap.add_argument('--title', required=True)
    ap.add_argument('--limit', type=int, default=1064, help='标题+正文 合计上限')
    ap.add_argument('--target', type=int, default=950, help='正文单独建议上限')
    a = ap.parse_args()

    raw = open(a.path, 'rb').read()
    s = raw.decode('utf-8')
    n, norm = count_backend(s)

    lines = [l for l in norm.split('\n') if l.strip()]
    body = [l for l in lines if not l.strip().startswith('#')]
    tags = [l for l in lines if l.strip().startswith('#')]
    pure = len(''.join(''.join(body).split()))
    nl = norm.rstrip('\n').count('\n')

    total = len(a.title) + n
    print('文件：%s' % os.path.basename(a.path))
    print('  标题        %4d 字' % len(a.title))
    print('  正文(后台口径) %4d 字  ← 含换行 %d 个' % (n, nl))
    print('  ─────────────────────────')
    print('  合计        %4d / %d   余量 %d   %s'
          % (total, a.limit, a.limit - total, '✅' if total <= a.limit else '❌超限'))
    print('  正文单独    %4d / %d   %s'
          % (n, a.target, '✅' if n <= a.target else '❌ 需再压 %d' % (n - a.target)))
    print()
    print('  （参考）去空白纯字 %d ｜ 段落 %d ｜ 标签 %d 个'
          % (pure, len(body), tags[0].count('#') if tags else 0))
    ok = total <= a.limit and n <= a.target
    print()
    print('判定：%s' % ('✅ 合规' if ok else '❌ 不合规'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
