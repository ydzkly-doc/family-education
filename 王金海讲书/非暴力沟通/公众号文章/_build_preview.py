# -*- coding: utf-8 -*-
"""生成《非暴力沟通》样板预览（第1、2篇），抽各发布包正文 body 合并。"""
import glob, re, os

BASE = os.path.dirname(os.path.abspath(__file__))
pkgs = sorted(glob.glob(os.path.join(BASE, "发布包_第*")))

arts = []
for pkg in pkgs:
    htmls = [f for f in glob.glob(os.path.join(pkg, "正文_*.html"))]
    if not htmls:
        continue
    s = open(htmls[0], encoding="utf-8").read()
    m = re.search(r"<body[^>]*>(.*?)</body>", s, re.S)
    body = m.group(1) if m else s
    # 去掉 body 上自带的页底色，交给预览容器
    body = re.sub(r'<body[^>]*>', '', body)
    num = re.search(r"第(\d+)篇", pkg).group(1)
    title = re.search(r"<title>(.*?)</title>", s, re.S)
    sub = re.search(r"共\s*7\s*篇\s*｜\s*([^<]+)", s)
    arts.append((num, (sub.group(1).strip() if sub else ""), body))

nav = "".join(
    f'<button class="cap {"on" if i==0 else ""}" onclick="go({i})">{n}·{t}</button>'
    for i,(n,t,_) in enumerate(arts))

sections = ""
for i,(n,t,body) in enumerate(arts):
    sections += f'<section class="art {"show" if i==0 else ""}" id="art{i}">{body}</section>\n'

html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>非暴力沟通 · 全部正文预览（共7篇）</title>
<style>
body{{margin:0;background:#eef2f1;font-family:'Microsoft YaHei',sans-serif;}}
.tocbar{{position:sticky;top:0;z-index:9;background:#4a6f6c;padding:12px 14px;box-shadow:0 2px 8px rgba(0,0,0,.15);}}
.tocbar .ttl{{color:#bfe0db;font-size:13px;letter-spacing:2px;margin-bottom:8px;text-align:center;}}
.caps{{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;}}
.cap{{border:1px solid #7fa9a4;background:transparent;color:#dcecea;font-size:13px;padding:6px 12px;border-radius:16px;cursor:pointer;}}
.cap.on{{background:#fff;color:#2f5753;font-weight:bold;border-color:#fff;}}
.art{{display:none;background:#f4f7f6;padding:18px 10px;}}
.art.show{{display:block;}}
.pager{{display:flex;justify-content:space-between;max-width:680px;margin:18px auto 40px;gap:10px;}}
.pager button{{flex:1;background:#4a6f6c;color:#fff;border:none;padding:12px;font-size:15px;border-radius:6px;cursor:pointer;}}
.pager .cnt{{flex:0 0 auto;background:transparent;color:#4a6f6c;align-self:center;font-size:14px;}}
</style></head><body>
<div class="tocbar"><div class="ttl">📑 非暴力沟通 · 样板预览（共 {len(arts)} 篇，共7篇）</div><div class="caps">{nav}</div></div>
{sections}
<div class="pager">
<button onclick="pg(-1)">◀ 上一篇</button>
<span class="cnt" id="cnt"></span>
<button onclick="pg(1)">下一篇 ▶</button>
</div>
<script>
var cur=0,total={len(arts)};
function show(i){{cur=Math.max(0,Math.min(total-1,i));
 document.querySelectorAll('.art').forEach(function(a,k){{a.classList.toggle('show',k===cur);}});
 document.querySelectorAll('.cap').forEach(function(b,k){{b.classList.toggle('on',k===cur);}});
 document.getElementById('cnt').textContent='第 '+(cur+1)+' 篇 / 共 '+total+' 篇';
 window.scrollTo({{top:0,behavior:'smooth'}});}}
function go(i){{show(i);}}
function pg(d){{show(cur+d);}}
document.addEventListener('keydown',function(e){{if(e.key==='ArrowLeft')pg(-1);if(e.key==='ArrowRight')pg(1);}});
show(0);
</script></body></html>"""

out = os.path.join(BASE, "非暴力沟通_全部正文预览_7篇.html")
open(out, "w", encoding="utf-8").write(html)
print("已生成:", out, "| 篇数:", len(arts))
