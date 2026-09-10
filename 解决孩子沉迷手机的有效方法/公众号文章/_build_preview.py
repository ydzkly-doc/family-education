# -*- coding: utf-8 -*-
"""把各发布包正文 body 抽成单页多 tab 预览，仅本地校对用。篇号可增删后重跑。

预览污染隔离（2026-09-06 铁律）：
  ① 读取源正文时先正则剥掉任何 data-* （双保险）
  ② 合并页输出到独立 _预览/ 子目录（纯派生副本），present_files 只开这份副本
  ③ --fix：就地剥掉所有发布包源正文里的 data-*
用法：python _build_preview.py [--fix]
"""
import re, glob, os, html, sys

BASE = os.path.dirname(os.path.abspath(__file__))
PKG = "发布包_第{n}篇_*"
DATA_RE = re.compile(r'\s*data-[a-zA-Z0-9_-]+="[^"]*"')

# (篇号, 短主题)
ITEMS = [
    (1, "三个成因·总纲"),
    (2, "环境模仿·那条路是我铺的"),
    (3, "学业受挫·没台阶下"),
    (4, "沟通·我一开口就推远"),
    (5, "网课·差在哪儿"),
    (6, "实战·三方面谈"),
    (7, "实战·一张纸的约定"),
    (8, "陪伴·有人等他"),
]


def find_body(n):
    ds = glob.glob(os.path.join(BASE, PKG.format(n=n)))
    if not ds:
        return None, None
    fs = glob.glob(os.path.join(ds[0], "正文_*.html"))
    if not fs:
        return ds[0], None
    return ds[0], fs[0]


def body_of(n):
    _, f = find_body(n)
    if not f:
        return ""
    t = open(f, encoding="utf-8").read()
    t = DATA_RE.sub("", t)  # 双保险：剥 data-*
    m = re.search(r"<body[^>]*>(.*?)</body>", t, re.S)
    return m.group(1) if m else ""


def do_fix():
    n_fixed = 0
    for f in sorted(glob.glob(os.path.join(BASE, "发布包_*", "正文_*.html"))):
        t = open(f, encoding="utf-8").read()
        t2 = DATA_RE.sub("", t)
        if t2 != t:
            open(f, "w", encoding="utf-8").write(t2)
            n_fixed += 1
            print("  fixed:", os.path.basename(f))
    print(f"--fix 完成：清洗 {n_fixed} 个文件")


if "--fix" in sys.argv:
    do_fix()

# 只保留实际存在的篇
ITEMS = [(n, t) for (n, t) in ITEMS if find_body(n)[1]]

nav = "".join(
    f'<button class="tab{" on" if i == 0 else ""}" onclick="go({i})">{n} · {html.escape(title)}</button>'
    for i, (n, title) in enumerate(ITEMS))

secs = []
for i, (n, title) in enumerate(ITEMS):
    secs.append(f'<section class="art{" show" if i == 0 else ""}" id="art{i}">{body_of(n)}</section>')

page = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>解决孩子沉迷手机的有效方法 · 全部正文预览（{len(ITEMS)}篇·校对用）</title>
<style>
body{{margin:0;background:#eae7f0;font-family:'Microsoft YaHei',sans-serif;padding-top:60px}}
#bar{{position:fixed;top:0;left:0;right:0;background:#655b79;padding:10px 12px;display:flex;flex-wrap:wrap;gap:8px;justify-content:center;z-index:99;box-shadow:0 2px 8px rgba(0,0,0,.15)}}
.tab{{border:1px solid #a396b8;background:#7a6f8f;color:#efeaf6;padding:6px 14px;border-radius:20px;font-size:13px;cursor:pointer}}
.tab.on{{background:#fff;color:#655b79;font-weight:bold;border-color:#fff}}
.art{{display:none;max-width:720px;margin:18px auto 40px}}
.art.show{{display:block}}
#pager{{max-width:720px;margin:0 auto 60px;display:flex;justify-content:space-between;padding:0 8px}}
#pager button{{background:#7a6f8f;color:#fff;border:none;padding:10px 22px;border-radius:8px;font-size:15px;cursor:pointer}}
#pos{{text-align:center;color:#6b6480;font-size:14px;margin:6px 0 0}}
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

outdir = os.path.join(BASE, "_预览")
os.makedirs(outdir, exist_ok=True)
out = os.path.join(outdir, f"解决孩子沉迷手机_全部正文预览_{len(ITEMS)}篇.html")
open(out, "w", encoding="utf-8").write(page)
print("written:", out)
