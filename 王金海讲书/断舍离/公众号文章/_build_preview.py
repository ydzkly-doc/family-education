# -*- coding: utf-8 -*-
"""把各发布包正文 body 抽成单页多 tab 预览，仅本地校对用。篇号自动读取，增删篇后重跑即可。

防污染（2026-09-06 铁律）：
  ① 读取源正文时先正则剥掉任何 data-*（双保险）
  ② 合并页输出到独立 _预览/ 子目录（纯派生副本），present_files 只开这份副本
  ③ --fix：就地剥掉所有发布包源正文里的 data-*
用法：python _build_preview.py [--fix]
"""
import re, glob, os, html, sys

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_RE = re.compile(r'\s*data-[a-zA-Z0-9_-]+="[^"]*"')
SERIES = os.path.basename(os.path.dirname(BASE))  # 上一级目录名 = 系列名


def scan_items():
    """扫描 发布包_第N篇_主题/ 目录，返回 [(篇号, 短主题), ...] 按篇号排序。"""
    items = []
    for d in glob.glob(os.path.join(BASE, "发布包_*")):
        m = re.search(r"第(\d+)篇[_-](.+)$", os.path.basename(d))
        if not m:
            continue
        items.append((int(m.group(1)), m.group(2).replace("_", "·")))
    return sorted(items)


def body_of(n):
    ds = glob.glob(os.path.join(BASE, f"发布包_第{n}篇_*"))
    if not ds:
        return ""
    fs = glob.glob(os.path.join(ds[0], "正文_*.html"))
    if not fs:
        return ""
    t = DATA_RE.sub("", open(fs[0], encoding="utf-8").read())
    m = re.search(r"<body[^>]*>(.*?)</body>", t, re.S)
    return m.group(1) if m else ""


if "--fix" in sys.argv:
    n = 0
    for f in sorted(glob.glob(os.path.join(BASE, "发布包_*", "正文_*.html"))):
        t = open(f, encoding="utf-8").read()
        t2 = DATA_RE.sub("", t)
        if t2 != t:
            open(f, "w", encoding="utf-8").write(t2)
            n += 1
            print("  fixed:", os.path.basename(f))
    print(f"--fix 完成：清洗 {n} 个文件")

ITEMS = scan_items()
nav = "".join(
    f'<button class="tab{" on" if i == 0 else ""}" onclick="go({i})">{n} · {html.escape(t)}</button>'
    for i, (n, t) in enumerate(ITEMS))
secs = []
for i, (n, t) in enumerate(ITEMS):
    secs.append(f'<section class="art{" show" if i == 0 else ""}" id="art{i}">{body_of(n)}</section>')

page = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(SERIES)} · 全部正文预览（{len(ITEMS)}篇·校对用）</title>
<style>
body{{margin:0;background:#eceae6;font-family:'Microsoft YaHei',sans-serif;padding-top:60px}}
#bar{{position:fixed;top:0;left:0;right:0;background:#4a4945;padding:10px 12px;display:flex;flex-wrap:wrap;gap:8px;justify-content:center;z-index:99;box-shadow:0 2px 8px rgba(0,0,0,.15)}}
.tab{{border:1px solid #8c8a84;background:#5d5b56;color:#eeece8;padding:6px 14px;border-radius:20px;font-size:13px;cursor:pointer}}
.tab.on{{background:#fff;color:#3a3833;font-weight:bold;border-color:#fff}}
.art{{display:none;max-width:720px;margin:18px auto 40px}}
.art.show{{display:block}}
#pager{{max-width:720px;margin:0 auto 60px;display:flex;justify-content:space-between;padding:0 8px}}
#pager button{{background:#5d5b56;color:#fff;border:none;padding:10px 22px;border-radius:8px;font-size:15px;cursor:pointer}}
#pos{{text-align:center;color:#6b6963;font-size:14px;margin:6px 0 0}}
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
out = os.path.join(outdir, f"{SERIES}_全部正文预览_{len(ITEMS)}篇.html")
open(out, "w", encoding="utf-8").write(page)
print("written:", out)
