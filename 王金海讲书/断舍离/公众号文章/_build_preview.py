# -*- coding: utf-8 -*-
"""断舍离系列 —— 全部正文预览生成脚本（已做「预览污染隔离」根治）。

根因背景：
  内置预览面板渲染 .html 时会给每个 DOM 节点注入 data-page-node-id，
  并把渲染结果【写回磁盘源文件】。为彻底隔离：
  1) 本脚本只读发布包里的【正式源正文】，读取时先正则剥掉一切 data-*（双保险）；
  2) 生成的合并预览页写到独立的 `_预览/` 目录 —— 该目录纯派生、不发布、
     随时可由本脚本重建，即使被预览面板注入 data-id 也无所谓（下次重建即覆盖）；
  3) 发布包内的正式正文 HTML【绝不直接送进预览面板】，从源头不被写回污染。

用法：
  python _build_preview.py            # 重建干净的合并预览页到 _预览/
  python _build_preview.py --fix      # 额外把所有发布包源正文的 data-* 剥干净（发布前保险）
"""
import os, re, sys, shutil

BASE = os.path.dirname(os.path.abspath(__file__))
PREVIEW_DIR = os.path.join(BASE, "_预览")

ARTS = [
    (1, "总纲·家里越满越累", "发布包_第1篇_家里越满越累", "正文_第1篇_家里越满越累.html"),
    (2, "执念·三种放不下",   "发布包_第2篇_舍不得的是执念", "正文_第2篇_舍不得的是执念.html"),
    (3, "方法·三句话取舍",   "发布包_第3篇_三句话取舍",   "正文_第3篇_三句话取舍.html"),
    (4, "沟通·北风和太阳",   "发布包_第4篇_北风和太阳",   "正文_第4篇_北风和太阳.html"),
    (5, "亲子·孩子的房间",   "发布包_第5篇_孩子的房间",   "正文_第5篇_孩子的房间.html"),
    (6, "收尾·整理自己",     "发布包_第6篇_整理自己",     "正文_第6篇_整理自己.html"),
]
TOTAL = 6

DATA_ATTR_RE = re.compile(r'\s*data-[a-zA-Z0-9_-]+="[^"]*"')

def strip_data_attrs(html):
    """剥掉所有 data-* 属性（预览面板注入物），其余原样保留。"""
    return DATA_ATTR_RE.sub("", html)

def extract_body_inner(path):
    s = strip_data_attrs(open(path, encoding="utf-8").read())  # 读源即剥污染
    m = re.search(r"<body[^>]*>(.*)</body>", s, re.S)
    return (m.group(1) if m else s).strip()

def fix_sources():
    """发布前保险：把所有发布包源正文里的 data-* 剥干净（就地）。"""
    n = 0
    for _num, _t, folder, fn in ARTS:
        p = os.path.join(BASE, folder, fn)
        if not os.path.exists(p):
            continue
        s = open(p, encoding="utf-8").read()
        clean = strip_data_attrs(s)
        if clean != s:
            open(p, "w", encoding="utf-8").write(clean)
            print("stripped data-* :", fn)
            n += 1
    print(f"源正文清洗完成，{n} 个文件被处理。")

def build():
    os.makedirs(PREVIEW_DIR, exist_ok=True)
    sections, nav = [], []
    for num, topic, folder, fn in ARTS:
        p = os.path.join(BASE, folder, fn)
        if not os.path.exists(p):
            print("MISSING:", p); continue
        sections.append(f'<section class="art" id="art{num}" style="display:none">{extract_body_inner(p)}</section>')
        nav.append(f'<button class="navbtn" data-n="{num}" onclick="go({num})">{num}·{topic}</button>')
    nums = [a[0] for a in ARTS]

    html = """<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>断舍离系列 · 全部正文预览（%d 篇）</title>
<style>
 body{margin:0;background:#e9eded;font-family:'Microsoft YaHei','微软雅黑',sans-serif;}
 .topbar{position:sticky;top:0;z-index:99;background:#2f5f5a;color:#fff;padding:12px 14px;box-shadow:0 2px 8px rgba(0,0,0,.15);}
 .topbar h2{margin:0 0 8px;font-size:16px;font-weight:600;}
 .nav{display:flex;flex-wrap:wrap;gap:8px;}
 .navbtn{border:1px solid #7fafa9;background:transparent;color:#dcebe8;font-size:13px;padding:5px 12px;border-radius:16px;cursor:pointer;}
 .navbtn.active{background:#fff;color:#2f5f5a;font-weight:bold;border-color:#fff;}
 .stage{max-width:720px;margin:18px auto;}
 .pager{max-width:720px;margin:0 auto 30px;display:flex;justify-content:space-between;gap:10px;padding:0 14px;}
 .pager button{flex:1;border:none;background:#4a857f;color:#fff;font-size:14px;padding:11px 10px;border-radius:8px;cursor:pointer;}
 .pager button:disabled{background:#b7c9c6;color:#eef4f3;cursor:default;}
 .curhint{text-align:center;color:#5a6a67;font-size:13px;margin:6px 0 0;}
</style></head><body>
<div class="topbar"><h2>断舍离 · 把家腾空 把心放下 ｜ 全部正文预览（共 %d 篇）· 本页为只读副本</h2>
<div class="nav">%s</div></div>
<p class="curhint" id="hint"></p>
<div class="stage">%s</div>
<div class="pager"><button id="prev" onclick="step(-1)">◀ 上一篇</button><button id="next" onclick="step(1)">下一篇 ▶</button></div>
<script>
var order=%s; var cur=order[0];
function show(n){
  document.querySelectorAll('.art').forEach(function(a){a.style.display=(a.id==='art'+n)?'block':'none';});
  document.querySelectorAll('.navbtn').forEach(function(b){b.classList.toggle('active',b.dataset.n==String(n));});
  var t=document.querySelector('.navbtn[data-n="'+n+'"]').textContent;
  document.getElementById('hint').textContent='第 '+n+' 篇 / 共 %d 篇 · '+t;
  document.getElementById('prev').disabled=(order.indexOf(n)<=0);
  document.getElementById('next').disabled=(order.indexOf(n)>=order.length-1);
  window.scrollTo(0,0);
}
function go(n){cur=n;show(n);}
function step(d){var i=order.indexOf(cur);var j=i+d;if(j>=0&&j<order.length){cur=order[j];show(cur);}}
document.addEventListener('keydown',function(e){if(e.key==='ArrowLeft')step(-1);if(e.key==='ArrowRight')step(1);});
show(cur);
</script></body></html>""" % (len(ARTS), TOTAL, "".join(nav), "".join(sections), str(nums), TOTAL)

    out = os.path.join(PREVIEW_DIR, "断舍离_全部正文预览_6篇.html")
    open(out, "w", encoding="utf-8").write(html)
    # 清理旧位置（成果根目录）的预览页，避免误用被污染的旧文件
    old = os.path.join(BASE, "断舍离_全部正文预览_6篇.html")
    old2 = os.path.join(BASE, "断舍离_全部正文预览_样板2篇.html")
    for o in (old, old2):
        if os.path.exists(o):
            os.remove(o); print("removed old preview:", os.path.basename(o))
    print("written:", out)

if __name__ == "__main__":
    if "--fix" in sys.argv:
        fix_sources()
    build()
