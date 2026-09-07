# -*- coding: utf-8 -*-
"""生成《解码青春期》全部正文预览（8篇），抽各发布包正文整页 table 合并。"""
import glob, re, os

BASE = os.path.dirname(os.path.abspath(__file__))
pkgs = sorted(glob.glob(os.path.join(BASE, "发布包_第*")),
              key=lambda p: int(re.search(r"第(\d+)篇", p).group(1)))

arts = []
for pkg in pkgs:
    htmls = glob.glob(os.path.join(pkg, "正文_*.html"))
    if not htmls:
        continue
    s = open(htmls[0], encoding="utf-8").read()
    m = re.search(r"<body[^>]*>(.*?)</body>", s, re.S)
    body = m.group(1) if m else s
    num = re.search(r"第(\d+)篇", pkg).group(1)
    # 副标题：取 第X篇·共N篇 ｜ 后的短主题
    sub = re.search(r"共\s*8\s*篇\s*｜\s*([^<]+)", s)
    t = sub.group(1).strip() if sub else ""
    # 主标题
    mt = re.search(r'font-size:26px[^>]*>(.*?)</p>', s, re.S)
    maintitle = re.sub(r"<[^>]+>", "", mt.group(1)).replace("<br>","").strip() if mt else ""
    arts.append((num, t, maintitle, body))

nav = "".join(
    f'<button class="cap {"on" if i==0 else ""}" onclick="go({i})">{n}</button>'
    for i,(n,t,mt,_) in enumerate(arts))

sections = ""
for i,(n,t,mt,body) in enumerate(arts):
    label = f"第{n}篇 · {mt}"
    sections += f'<section class="art {"show" if i==0 else ""}" id="art{i}"><div class="arttag">{label}</div>{body}</section>\n'

html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>解码青春期 · 全部正文预览（共8篇）</title>
<style>
body{{margin:0;background:#ece6df;font-family:'Microsoft YaHei',sans-serif;}}
.tocbar{{position:sticky;top:0;z-index:9;background:#b06a48;padding:12px 14px;box-shadow:0 2px 8px rgba(0,0,0,.18);}}
.tocbar .ttl{{color:#f3e2d4;font-size:13px;letter-spacing:2px;margin-bottom:8px;text-align:center;}}
.caps{{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;}}
.cap{{border:1px solid #d9b49a;background:transparent;color:#f6e7da;font-size:14px;width:38px;height:34px;border-radius:17px;cursor:pointer;}}
.cap.on{{background:#fff;color:#93553a;font-weight:bold;border-color:#fff;}}
.art{{display:none;background:#f5f3ef;padding:14px 8px;}}
.art.show{{display:block;}}
.arttag{{max-width:680px;margin:0 auto 10px;text-align:center;color:#93553a;font-weight:bold;font-size:15px;background:#f0e2d4;border-radius:6px;padding:8px;}}
.pager{{display:flex;justify-content:space-between;max-width:680px;margin:18px auto 40px;gap:10px;}}
.pager button{{flex:1;background:#b06a48;color:#fff;border:none;padding:12px;font-size:15px;border-radius:6px;cursor:pointer;}}
.pager .cnt{{flex:0 0 auto;background:transparent;color:#93553a;align-self:center;font-size:14px;}}
</style></head><body>
<div class="tocbar"><div class="ttl">📑 解码青春期 · 全部正文预览（共 {len(arts)} 篇）</div><div class="caps">{nav}</div></div>
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

out = os.path.join(BASE, "解码青春期_全部正文预览_8篇.html")
open(out, "w", encoding="utf-8").write(html)
print("已生成:", os.path.basename(out), "| 篇数:", len(arts))
for n,t,mt,_ in arts:
    print(f"  第{n}篇: {mt}")
