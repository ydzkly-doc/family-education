# -*- coding: utf-8 -*-
"""把各发布包正文 body 抽成单页多 tab 预览，仅本地校对用。篇号可增删后重跑。"""
import re, glob, os, html

BASE = os.path.dirname(os.path.abspath(__file__))
PKG = "发布包_第{n}篇_*"
# (篇号, 短主题)
ITEMS = [(1, "总纲·顾问型家长"), (2, "白帽·内驱力"), (3, "红帽·情绪自控"),
         (4, "黄帽·习惯自控"), (5, "蓝帽·竞争力"), (6, "黑帽·抗逆力")]

def body_of(n):
    ds = glob.glob(os.path.join(BASE, PKG.format(n=n)))
    if not ds: return ""
    fs = glob.glob(os.path.join(ds[0], "正文_*.html"))
    if not fs: return ""
    t = open(fs[0], encoding="utf-8").read()
    m = re.search(r"<body[^>]*>(.*?)</body>", t, re.S)
    return m.group(1) if m else ""

nav = "".join(
    f'<button class="tab{" on" if i==0 else ""}" onclick="go({i})">{n} · {html.escape(title)}</button>'
    for i,(n,title) in enumerate(ITEMS))

secs = []
for i,(n,title) in enumerate(ITEMS):
    b = body_of(n)
    secs.append(f'<section class="art{" show" if i==0 else ""}" id="art{i}">{b}</section>')

page = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>五顶学习帽 · 全部正文预览（{len(ITEMS)}篇·校对用）</title>
<style>
body{{margin:0;background:#e9edec;font-family:'Microsoft YaHei',sans-serif;padding-top:60px}}
#bar{{position:fixed;top:0;left:0;right:0;background:#2f5753;padding:10px 12px;display:flex;flex-wrap:wrap;gap:8px;justify-content:center;z-index:99;box-shadow:0 2px 8px rgba(0,0,0,.15)}}
.tab{{border:1px solid #7fa6a1;background:#3f6f6a;color:#dfeeea;padding:6px 14px;border-radius:20px;font-size:13px;cursor:pointer}}
.tab.on{{background:#fff;color:#2f5753;font-weight:bold;border-color:#fff}}
.art{{display:none;max-width:720px;margin:18px auto 40px}}
.art.show{{display:block}}
#pager{{max-width:720px;margin:0 auto 60px;display:flex;justify-content:space-between;padding:0 8px}}
#pager button{{background:#3f6f6a;color:#fff;border:none;padding:10px 22px;border-radius:8px;font-size:15px;cursor:pointer}}
#pos{{text-align:center;color:#5a6663;font-size:14px;margin:6px 0 0}}
</style></head><body>
<div id="bar">{nav}</div>
{''.join(secs)}
<p id="pos"></p>
<div id="pager"><button onclick="step(-1)">◀ 上一篇</button><button onclick="step(1)">下一篇 ▶</button></div>
<script>
var N={len(ITEMS)},cur=0;
function show(i){{cur=(i+N)%N;document.querySelectorAll('.art').forEach((a,k)=>a.classList.toggle('show',k===cur));
document.querySelectorAll('.tab').forEach((b,k)=>b.classList.toggle('on',k===cur));
document.getElementById('pos').textContent='第 '+(cur+1)+' 篇 / 共 '+N+' 篇';window.scrollTo(0,0);}}
function go(i){{show(i);}}function step(d){{show(cur+d);}}
document.addEventListener('keydown',e=>{{if(e.key==='ArrowLeft')step(-1);if(e.key==='ArrowRight')step(1);}});
show(0);
</script></body></html>"""

out = os.path.join(BASE, f"五顶学习帽_全部正文预览_{len(ITEMS)}篇.html")
open(out, "w", encoding="utf-8").write(page)
print("written:", out)
