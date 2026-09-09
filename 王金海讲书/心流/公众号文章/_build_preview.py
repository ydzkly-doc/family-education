# -*- coding: utf-8 -*-
"""构建《心流》系列「全部正文预览」单文件（仅本地校对用，不进发布包、不发布）。
用法: python _build_preview.py
扫描 发布包_第X篇_* 目录里的 正文_*.html，按篇号排序抽 <body> 合并。"""
import os, re, glob, html

BASE = os.path.dirname(os.path.abspath(__file__))
dirs = []
for d in glob.glob(os.path.join(BASE, "发布包_第*篇_*")):
    m = re.search(r"第(\d+)篇", os.path.basename(d))
    if m and os.path.isdir(d):
        dirs.append((int(m.group(1)), d))
dirs.sort()

arts = []
nav = []
for num, d in dirs:
    files = glob.glob(os.path.join(d, "正文_*.html"))
    if not files:
        continue
    raw = open(files[0], encoding="utf-8").read()
    body = re.search(r"<body[^>]*>(.*?)</body>", raw, re.S | re.I)
    inner = body.group(1) if body else raw
    # 取主题名
    tm = re.search(r"共\s*6\s*篇\s*｜\s*(.*?)</p>", inner)
    topic = tm.group(1) if tm else ""
    title_m = re.search(r"发布包_第\d+篇_(.*)$", os.path.basename(d))
    short = title_m.group(1) if title_m else f"第{num}篇"
    nav.append((num, short, topic))
    arts.append(f'<section class="art" id="art{num}" style="display:none;">{inner}</section>')

nav_btns = "".join(
    f'<button class="navbtn" data-n="{n}" onclick="go({n})">{n}·{html.escape(s)}</button>'
    for n, s, t in nav
)
total = len(nav)
sections = "\n".join(arts)

page = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>心流系列 · 全部正文预览（{total}篇·本地校对用）</title>
<style>
body{{margin:0;background:#dfe6e5;font-family:-apple-system,"Microsoft YaHei",sans-serif;}}
.topbar{{position:sticky;top:0;z-index:99;background:#234f4d;color:#fff;padding:12px 14px;box-shadow:0 2px 8px rgba(0,0,0,.15);}}
.topbar h2{{margin:0 0 8px;font-size:16px;font-weight:600;}}
.nav{{display:flex;flex-wrap:wrap;gap:8px;}}
.navbtn{{border:1px solid #7fb0ad;background:transparent;color:#dfeeea;padding:6px 12px;border-radius:16px;font-size:13px;cursor:pointer;}}
.navbtn.on{{background:#fff;color:#234f4d;font-weight:bold;border-color:#fff;}}
.status{{margin-top:8px;font-size:13px;color:#bfe0dd;}}
.pager{{max-width:680px;margin:14px auto;display:flex;justify-content:space-between;padding:0 12px;}}
.pager button{{background:#2f6d6b;color:#fff;border:none;padding:9px 18px;border-radius:8px;font-size:14px;cursor:pointer;}}
.art{{max-width:680px;margin:0 auto;}}
.art.show{{display:block!important;}}
</style></head><body>
<div class="topbar"><h2>读懂《心流》· 全部正文预览（{total}篇，仅本地校对，勿发布）</h2>
<div class="nav">{nav_btns}</div>
<div class="status" id="st"></div></div>
<div class="pager"><button onclick="prev()">◀ 上一篇</button><button onclick="next()">下一篇 ▶</button></div>
{sections}
<div class="pager"><button onclick="prev()">◀ 上一篇</button><button onclick="next()">下一篇 ▶</button></div>
<script>
const total={total};
function show(n){{
  n=Math.max(1,Math.min(total,n));
  document.querySelectorAll('.art').forEach(a=>{{a.classList.remove('show');a.style.display='none';}});
  const el=document.getElementById('art'+n);
  if(el){{el.classList.add('show');el.style.display='block';}}
  document.querySelectorAll('.navbtn').forEach(b=>b.classList.toggle('on',b.dataset.n==String(n)));
  const btn=document.querySelector('.navbtn[data-n="'+n+'"]');
  document.getElementById('st').textContent='第 '+n+' 篇 / 共 {total} 篇'+(btn?' · '+btn.textContent.replace(/^\\d+·/,''):'');
  window.scrollTo({{top:0,behavior:'smooth'}});
}}
function prev(){{show(cur()-1);}}
function next(){{show(cur()+1);}}
function cur(){{const on=document.querySelector('.navbtn.on');return on?parseInt(on.dataset.n):0;}}
document.addEventListener('keydown',e=>{{if(e.key==='ArrowLeft')prev();if(e.key==='ArrowRight')next();}});
show(1);
</script></body></html>"""

out = os.path.join(BASE, f"心流系列_全部正文预览_{total}篇.html")
open(out, "w", encoding="utf-8").write(page)
print("生成:", out, "篇数:", total)
