# -*- coding: utf-8 -*-
"""微信兼容修复 v2（针对 孩子不上学第1篇、非暴力沟通第1篇）：
微信对 <td>/<section> 上的 color 继承给内部文字不稳定；对 <p>/<span>/<b> 自身内联 color 保留好。
做法：
- 对每个带 style 的 <td ...>，解析其 color；把该 color 显式注入到此 td 直接包含的、
  尚无 color 的 <p>、<b>、<strong>、<span> 标签 style 里（注入在开标签）。
- section 上的 color 同样下沉到内部无色 p/span。
- 保留背景/圆角/padding 等在 td/section 上（这些微信保留）。
- 不动 table 布局。
"""
import re, os

FILES = [
 r"D:/个人资料/家庭教育/孩子不上学了怎么办/公众号文章/发布包_第1篇_接错话/正文_第1篇_接错话.html",
 r"D:/个人资料/家庭教育/王金海讲书/非暴力沟通/公众号文章/发布包_第1篇_总纲_三天没说话/正文_第1篇_我吼完孩子那句你懂什么他三天没跟我说话.html",
]

def get_color(style):
    m = re.search(r'color:\s*(#[0-9a-fA-F]{3,6})', style)
    return m.group(1) if m else None

def inject_color_into(tag_html, color):
    """把 color 注入到这段 inner html 里所有 <p>/<b>/<strong>/<span> 开标签
    若该标签已有 color 则跳过（已有色优先）。"""
    def repl(m):
        tag = m.group(1)            # p / b / strong / span
        attrs = m.group(2) or ""    # 开标签属性
        if attrs.startswith('style="'):
            sm = re.search(r'style="([^"]*)"', attrs)
            st = sm.group(1)
            if 'color:' in st:
                return m.group(0)   # 已有色，保留
            newst = st.rstrip(';') + f';color:{color}'
            attrs = attrs.replace(f'style="{st}"', f'style="{newst}"', 1)
        else:
            # 无 style，补一个（放最前，保留原属性）
            attrs = f' style="color:{color}"' + attrs
        return f'<{tag}{attrs}>'
    pattern = re.compile(r'<(p|b|strong|span)(\s[^>]*?)?>(?!\s*/)', re.S)
    return pattern.sub(repl, tag_html)

for f in FILES:
    h = open(f, encoding='utf-8').read()
    out = h

    # 处理 <td ... style="...color:X..."> ... </td>：把该 td 内部（不含嵌套 table 的下一层文字）下沉色
    # 用逐个 td 匹配（td 可嵌套，用 finditer 后对内部 html 处理；为避免重复，直接对每个开 td 处理其 color 到其后内容）
    # 简化：针对每个 <td style=...color:X...>，取 color，然后在它后面到对应 </td> 的区段注入。
    # 由于 td 嵌套复杂，采用：全局扫描每个“含 color 的 td 开标签”，注入色到它之后 1500 字符内的无色文字标签——
    # 不安全。改用栈式分段处理。

    # —— 用更稳的方式：匹配 <td ...>INNER</td> 非贪婪会被嵌套打乱；
    # 这里文件是单行，改用手写栈切分。
    tokens = re.split(r'(<td\b[^>]*>|</td>)', h)
    # tokens 交替: 文本/标签
    stack_colors = []   # 每个 td 的 color
    result = []
    td_open_re = re.compile(r'<td\b([^>]*)>')
    for tok in tokens:
        mo = td_open_re.fullmatch(tok) if tok.startswith('<td') else None
        if tok.startswith('</td>'):
            if stack_colors: stack_colors.pop()
            result.append(tok)
            continue
        m = td_open_re.match(tok) if tok.startswith('<td') else None
        if m:
            attrs = m.group(1)
            sm = re.search(r'style="([^"]*)"', attrs)
            col = get_color(sm.group(1)) if sm else None
            result.append(tok)
            stack_colors.append(col)
        else:
            # 文本/其他标签块：若当前 td 有 color，给其中无色文字标签注入
            if stack_colors:
                col = stack_colors[-1]
                if col:
                    tok = inject_color_into(tok, col)
            result.append(tok)
    out = ''.join(result)

    open(f, 'w', encoding='utf-8').write(out)
    print("FIXED-v2:", os.path.basename(f))
