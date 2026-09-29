from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "_预览" / "刻意练习_全部正文预览_5篇.html"
packages = sorted(ROOT.glob("发布包_第*篇_*"), key=lambda p: int(re.search(r"第(\d+)篇", p.name).group(1)))
articles = []
for package in packages:
    body = next(package.glob("正文_第*篇_*.html"))
    html = body.read_text(encoding="utf-8")
    title_match = re.search(r'<p[^>]*font-size:26px[^>]*>(.*?)</p>', html, re.S)
    title = re.sub(r"<[^>]+>", "", title_match.group(1)).strip() if title_match else package.name
    articles.append((title, html))

buttons = "".join(f'<button data-i="{i}" class="{"on" if i == 0 else ""}">{i+1} {title}</button>' for i, (title, _) in enumerate(articles))
panels = "".join(f'<section class="{"art show" if i == 0 else "art"}">{html}</section>' for i, (_, html) in enumerate(articles))
n = len(articles)
page = f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>刻意练习｜全部正文预览｜{n}篇</title>
<style>body{{margin:0;background:#e9edea;font-family:"Microsoft YaHei",sans-serif;color:#2f3c39}}main{{max-width:900px;margin:auto;padding:24px 14px 50px}}.nav{{position:sticky;top:0;z-index:2;background:#e9edeaee;padding:12px 0;display:flex;gap:8px;flex-wrap:wrap;justify-content:center}}.nav button{{border:1px solid #9eb3ae;background:#fff;color:#315f5a;border-radius:18px;padding:7px 13px;cursor:pointer}}.nav button.on{{background:#315f5a;color:#fff}}.art{{display:none}}.art.show{{display:block}}.turn{{display:flex;justify-content:space-between;margin-top:14px}}.turn button{{border:0;border-radius:7px;background:#315f5a;color:#fff;padding:9px 16px;cursor:pointer}}.turn button:disabled{{opacity:.35}}</style></head><body><main>
<p style="margin:0;text-align:center;color:#315f5a;font-size:30px;font-weight:700;">《刻意练习》全部正文预览</p><p id="status" style="text-align:center;color:#6f7773;margin:8px 0 12px;">第1篇 / 共{n}篇</p><nav class="nav">{buttons}</nav>{panels}<p class="turn"><button id="prev" disabled>上一篇</button><button id="next">下一篇</button></p></main>
<script>let i=0;const n={n},ps=[...document.querySelectorAll('.art')],bs=[...document.querySelectorAll('.nav button')],st=document.getElementById('status'),prev=document.getElementById('prev'),next=document.getElementById('next');function show(x){{i=Math.max(0,Math.min(n-1,x));ps.forEach((p,k)=>p.classList.toggle('show',k===i));bs.forEach((b,k)=>b.classList.toggle('on',k===i));st.textContent=`第${{i+1}}篇 / 共${{n}}篇`;prev.disabled=i===0;next.disabled=i===n-1;scrollTo({{top:0,behavior:'smooth'}})}}bs.forEach(b=>b.onclick=()=>show(+b.dataset.i));prev.onclick=()=>show(i-1);next.onclick=()=>show(i+1);addEventListener('keydown',e=>{{if(e.key==='ArrowLeft')show(i-1);if(e.key==='ArrowRight')show(i+1)}});</script></body></html>'''
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(page, encoding="utf-8")
print(OUT)
