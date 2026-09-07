# -*- coding: utf-8 -*-
"""
爱的五种语言 第1篇：div 骨架 -> p 骨架（对齐青春期30讲成功案例）
1) <div style=...> -> <p style=...>；</div> -> </p>
2) 头部白字大标题里的 <br> 拆成两个独立居中 <p>（第二行白色不断继承）
3) 剥 data-* 残留（本篇为0，兜底）
4) 之后交给 v3：td/section 色下沉到裸文字 span
"""
import re, sys, subprocess, os

f=sys.argv[1]
h=open(f,encoding="utf-8").read()

# 1) div -> p
h=re.sub(r'<div\b','<p',h)
h=h.replace('</div>','</p>')

# 2) 剥 data-*
h=re.sub(r'\s*data-[a-zA-Z0-9\-]+="[^"]*"','',h)

# 3) 头部白字标题拆 br：找 color:#ffffff 的 <p ...>...<br>...</p>（大标题）
def split_white_title(m):
    open_tag=m.group(1); inner=m.group(2)
    if '<br' not in inner: return m.group(0)
    parts=re.split(r'<br\s*/?>',inner)
    parts=[p.strip() for p in parts if p.strip()]
    if len(parts)<2: return m.group(0)
    # 构造两个同 style 的 p，各自居中块
    out=[]
    for idx,p in enumerate(parts):
        mb = 'margin:0 0 10px;' if idx<len(parts)-1 else 'margin:0 0 14px;'
        # 替换原 open style 里的 margin
        style=re.sub(r'margin[^;]*;?','',open_tag)
        style=style.strip()
        out.append(f'<p style="{mb}font-size:27px;line-height:1.5;font-weight:bold;color:#ffffff;text-align:center;display:block;">{p}</p>')
    return "".join(out)

# 匹配白字标题 p（含 <br>）
h=re.sub(r'<p style="([^"]*color:#ffffff[^"]*)">([^<]*(?:<br\s*/?>[^<]*)*)</p>',
         lambda m: split_white_title(type("M",(),{"group":lambda s,i:[None,m.group(1),m.group(2),m.group(0)][i]})()),
         h)

open(f,"w",encoding="utf-8").write(h)
print("div->p 完成；<p>:",len(re.findall(r'<p\b',h))," <div>:",len(re.findall(r'<div',h)),
      " 白字块br残留:", len(re.findall(r'color:#ffffff[^>]*>[^<]*<br',h)))
