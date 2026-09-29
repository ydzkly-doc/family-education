# -*- coding: utf-8 -*-
"""仅修复《解码青春期》第1-3篇，供微信粘贴验证。
修复点：
1) 剥掉微信注入的 data-page-node-id；
2) 标题色块白字主标题：把 <br> 拆成两个各自显式 color:#ffffff 的 <p>（白字+<br>微信会丢色）；
3) 所有 <p> 若无 color 显式补正文深色 #3a322c（不依赖继承）；
4) 标题块内顶部小字/副标颜色保留浅色但写成显式。
"""
import glob, os, re

BASE = r"D:/个人资料/家庭教育/王金海讲书/解码青春期/公众号文章"
files = sorted(glob.glob(os.path.join(BASE, "发布包_第*", "正文_*.html")),
               key=lambda p: int(re.search(r"第(\d+)篇", p).group(1)))[:3]
BODY = "#3a322c"

def fix_title_p(s):
    inner = re.search(r'>(.*?)</p>', s, re.S).group(1)
    if '<br' not in inner:
        return re.sub(r'color:#[0-9a-fA-F]{3,6}', 'color:#ffffff', s, count=1)
    parts = [p.strip() for p in re.split(r'<br\s*/?>', inner) if p.strip()]
    out = ""
    for i, pt in enumerate(parts):
        mb = "margin:0 0 12px;" if i < len(parts)-1 else "margin:0 0 14px;"
        out += (f'<p style="{mb}font-size:26px;line-height:1.5;'
                f'font-weight:bold;color:#ffffff;text-align:center;">{pt}</p>')
    return out

for f in files:
    h = open(f, encoding="utf-8").read()
    h = re.sub(r'\s*data-page-node-id="[^"]*"', '', h)

    # 标题块（含 background:#b06a48 的 td）内主标题处理
    def title_repl(m):
        block = m.group(0)
        block = re.sub(r'<p style="[^"]*font-size:26px[^"]*">.*?</p>',
                       lambda mm: fix_title_p(mm.group(0)), block, flags=re.S)
        return block
    h = re.sub(r'<td[^>]*background:#b06a48[^>]*>.*?</td>', title_repl, h, flags=re.S)

    # 所有无 color 的 <p> 补正文深色
    def p_repl(m):
        s = m.group(0)
        stm = re.search(r'style="([^"]*)"', s)
        st = stm.group(1) if stm else ""
        if 'color:' in st:
            return s
        newst = st.rstrip(';') + f';color:{BODY}'
        return s.replace(f'style="{st}"', f'style="{newst}"', 1)
    h = re.sub(r'<p style="[^"]*">.*?</p>', p_repl, h, flags=re.S)

    open(f, "w", encoding="utf-8").write(h)
    print("FIXED:", os.path.basename(f))
