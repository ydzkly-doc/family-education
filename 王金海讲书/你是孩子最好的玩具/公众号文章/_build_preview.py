# -*- coding: utf-8 -*-
"""把各发布包正文 <body> 内合并为单一预览页（仅本地校对，不发布）。"""
import re, os, sys

BASE = os.path.dirname(os.path.abspath(__file__))

# (篇号, 短主题, 正文文件相对路径)
ARTS = [
    (1, "总纲·四个误区", os.path.join("发布包_第1篇_爱的四个误区", "正文_第1篇_爱的四个误区.html")),
    (2, "控制型父母",     os.path.join("发布包_第2篇_为你好为什么伤人", "正文_第2篇_为你好为什么伤人.html")),
    (3, "接纳感受",       os.path.join("发布包_第3篇_别哭关上心门", "正文_第3篇_别哭关上心门.html")),
    (4, "奖励与内动力",   os.path.join("发布包_第4篇_奖励偷走内动力", "正文_第4篇_奖励偷走内动力.html")),
    (5, "惩罚与直接后果", os.path.join("发布包_第5篇_让后果说话", "正文_第5篇_让后果说话.html")),
    (6, "五步法",         os.path.join("发布包_第6篇_情感引导五步法", "正文_第6篇_情感引导五步法.html")),
    (7, "回望与速览",     os.path.join("发布包_第7篇_多希望小时候读过", "正文_第7篇_多希望小时候读过.html")),
]

def extract_body(path):
    html = open(path, encoding="utf-8").read()
    m = re.search(r"<body[^>]*>(.*?)</body>", html, re.S)
    return m.group(1).strip() if m else html

sections = []
navs = []
for n, topic, rel in ARTS:
    body = extract_body(os.path.join(BASE, rel))
    sections.append(f'<section class="art" id="art{n}">\n<div class="arttag">第 {n} 篇 / 共 {len(ARTS)} 篇 · {topic}</div>\n{body}\n</section>')
    navs.append(f'<button class="nav" data-n="{n}" onclick="go({n})">{n}<span class="nt">{topic}</span></button>')

page = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>你就是孩子最好的玩具 · 全部正文预览（7 篇）</title>
<style>
 body{margin:0;background:#ece7df;font-family:-apple-system,"Microsoft YaHei",sans-serif;}
 .topbar{position:sticky;top:0;z-index:9;background:#b06a48;padding:12px 14px;box-shadow:0 2px 8px rgba(0,0,0,.15);}
 .topbar h1{margin:0 0 10px;color:#fff;font-size:16px;text-align:center;font-weight:600;}
 .navs{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;}
 .nav{border:1px solid rgba(255,255,255,.5);background:transparent;color:#f3e2d4;border-radius:20px;padding:5px 14px;font-size:14px;cursor:pointer;line-height:1.4;}
 .nav .nt{font-size:11px;margin-left:5px;opacity:.85;}
 .nav.on{background:#fff;color:#93553a;font-weight:700;border-color:#fff;}
 .wrap{max-width:720px;margin:18px auto;}
 .art{display:none;background:transparent;}
 .art.show{display:block;}
 .arttag{max-width:680px;margin:0 auto 10px;text-align:center;color:#93553a;font-size:13px;font-weight:600;background:#faf3ec;border:1px solid #ecd9c6;border-radius:16px;padding:6px 10px;}
 .pager{max-width:680px;margin:16px auto 40px;display:flex;justify-content:space-between;gap:10px;}
 .pager button{flex:1;border:none;background:#b06a48;color:#fff;padding:12px;border-radius:8px;font-size:15px;cursor:pointer;}
 .pager button:disabled{opacity:.35;cursor:default;}
</style></head><body>
<div class="topbar">
 <h1>《你就是孩子最好的玩具》读书笔记 · 全部正文预览（共 __N__ 篇）</h1>
 <div class="navs">__NAVS__</div>
</div>
<div class="wrap">
__SECTIONS__
<div class="pager">
 <button id="prev" onclick="step(-1)">◀ 上一篇</button>
 <button id="next" onclick="step(1)">下一篇 ▶</button>
</div>
</div>
<script>
 const total=__N__;let cur=1;
 function show(n){cur=Math.max(1,Math.min(total,n));
  document.querySelectorAll('.art').forEach(a=>a.classList.toggle('show',a.id==='art'+cur));
  document.querySelectorAll('.nav').forEach(b=>b.classList.toggle('on',+b.dataset.n===cur));
  document.getElementById('prev').disabled=cur===1;
  document.getElementById('next').disabled=cur===total;
  window.scrollTo({top:0,behavior:'smooth'});}
 function go(n){show(n);} function step(d){show(cur+d);}
 document.addEventListener('keydown',e=>{if(e.key==='ArrowLeft')step(-1);if(e.key==='ArrowRight')step(1);});
 show(1);
</script>
</body></html>"""

page = page.replace("__N__", str(len(ARTS))).replace("__NAVS__", "".join(navs)).replace("__SECTIONS__", "\n".join(sections))
out = os.path.join(BASE, "你是孩子最好的玩具_全部正文预览_7篇.html")
open(out, "w", encoding="utf-8").write(page)
print("written:", out)
