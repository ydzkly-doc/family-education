# -*- coding: utf-8 -*-
"""
重建全部正文预览_通用.py
扫描每个系列 公众号文章/ 下的 发布包_第X篇_*，抽取各正文 HTML 的 <body> 内容，
合并成一个带篇号导航 + 上/下一篇 + 键盘←/→ 的预览页（仅本地校对用，不发布）。
用法：python 重建全部正文预览.py [系列公众号文章目录 ...]；不传则自动发现全部。
"""
import os, re, sys, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 家庭教育/

def find_series_dirs():
    dirs = []
    for p in glob.glob(os.path.join(ROOT, "**", "公众号文章"), recursive=True):
        if "_backup" in p or os.sep+"_backup" in p:
            continue
        if glob.glob(os.path.join(p, "发布包_*")):
            dirs.append(p)
    return sorted(set(dirs))

def extract_body(path):
    txt = open(path, encoding="utf-8").read()
    m = re.search(r"<body[^>]*>(.*?)</body>", txt, re.S | re.I)
    inner = m.group(1) if m else txt
    inner = re.sub(r"<script.*?</script>", "", inner, flags=re.S | re.I)
    return inner.strip()

def series_name(d):
    return os.path.basename(os.path.dirname(d))

def collect_articles(sdir):
    """返回 [(num, topic, body)]，按篇号排序。topic 取文件夹名里'第X篇_'之后部分。"""
    arts = []
    for folder in sorted(glob.glob(os.path.join(sdir, "发布包_*"))):
        bn = os.path.basename(folder)
        mnum = re.search(r"第(\d+)篇[_\-]?(.*)", bn)
        if not mnum:
            continue
        num = int(mnum.group(1))
        topic = mnum.group(2) or bn
        # 找正文 html（取 正文_第X篇*.html，排除说教版/安卓测试）
        # 兼容新结构：优先查「长图文发布包/」，否则回退包根
        _cdir = os.path.join(folder, "长图文发布包")
        if not os.path.isdir(_cdir):
            _cdir = folder
        cands = [f for f in glob.glob(os.path.join(_cdir, "正文_*.html"))
                 if "说教版" not in f and "安卓测试" not in os.path.basename(f)]
        if not cands:
            continue
        # 优先文件名含篇号的
        cands.sort(key=lambda f: (f"第{num}篇" not in os.path.basename(f), f))
        body = extract_body(cands[0])
        arts.append((num, topic, body))
    arts.sort(key=lambda x: x[0])
    return arts

def build(sdir):
    name = series_name(sdir)
    arts = collect_articles(sdir)
    if not arts:
        return None
    n = len(arts)
    nav = []
    secs = []
    for i,(num,topic,body) in enumerate(arts):
        nav.append(f'<button class="navbtn" data-target="art{num}" onclick="go({num})">'
                   f'<span class="n">{num}</span><span class="t">{topic}</span></button>')
        secs.append(f'<section class="art" id="art{num}">\n<div class="arttag">第 {num} 篇 / 共 {n} 篇 · {topic}</div>\n{body}\n</section>')
    out = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{name} · 全部正文顺序预览（共{n}篇）</title>
<style>
*{{box-sizing:border-box;}}
body{{margin:0;font-family:-apple-system,"Microsoft YaHei",sans-serif;background:#f2f3f5;color:#222;}}
.topbar{{position:sticky;top:0;z-index:99;background:#fff;border-bottom:1px solid #e3e3e3;box-shadow:0 2px 8px rgba(0,0,0,.05);padding:10px 12px;}}
.topbar h1{{font-size:15px;margin:0 0 8px;text-align:center;color:#333;}}
.nav{{display:flex;flex-wrap:wrap;gap:6px;justify-content:center;}}
.navbtn{{border:1px solid #d8d8d8;background:#fafafa;color:#555;border-radius:16px;padding:4px 10px;font-size:12px;cursor:pointer;display:flex;align-items:center;gap:4px;}}
.navbtn .n{{background:#e8e8e8;border-radius:50%;width:18px;height:18px;display:inline-flex;align-items:center;justify-content:center;font-weight:bold;font-size:11px;}}
.navbtn.active{{background:#b06a48;border-color:#b06a48;color:#fff;}}
.navbtn.active .n{{background:rgba(255,255,255,.3);color:#fff;}}
.wrap{{max-width:720px;margin:0 auto;padding:16px 10px 90px;}}
.art{{display:none;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 1px 6px rgba(0,0,0,.06);}}
.art.show{{display:block;}}
.arttag{{background:#f7f3ec;color:#8a6d4f;font-size:13px;text-align:center;padding:8px;font-weight:bold;border-bottom:1px solid #eee;}}
.pager{{position:fixed;bottom:0;left:0;right:0;display:flex;justify-content:space-between;gap:10px;padding:10px 14px;background:rgba(255,255,255,.96);border-top:1px solid #e5e5e5;z-index:98;}}
.pager button{{flex:1;border:1px solid #ccc;background:#fff;border-radius:8px;padding:10px;font-size:14px;cursor:pointer;color:#444;}}
.pager button:disabled{{opacity:.4;cursor:default;}}
.counter{{text-align:center;font-size:12px;color:#999;padding:6px;}}
</style></head><body>
<div class="topbar"><h1>{name} · 全部正文预览（共 {n} 篇）</h1><div class="nav">{''.join(nav)}</div></div>
<div class="wrap">
{''.join(secs)}
<div class="counter" id="counter"></div>
</div>
<div class="pager"><button id="prev" onclick="step(-1)">◀ 上一篇</button><button id="next" onclick="step(1)">下一篇 ▶</button></div>
<script>
var order=[{','.join(str(a[0]) for a in arts)}];
var cur=order[0];
function show(id){{
  document.querySelectorAll('.art').forEach(function(a){{a.classList.remove('show');}});
  document.querySelectorAll('.navbtn').forEach(function(b){{b.classList.remove('active');}});
  var el=document.getElementById('art'+id); if(el) el.classList.add('show');
  var btn=document.querySelector('.navbtn[data-target="art'+id+'"]'); if(btn) btn.classList.add('active');
  cur=id; var i=order.indexOf(id);
  document.getElementById('counter').textContent='第 '+id+' 篇 / 共 '+order.length+' 篇';
  document.getElementById('prev').disabled=(i<=0);
  document.getElementById('next').disabled=(i>=order.length-1);
  window.scrollTo(0,0);
}}
function go(id){{show(id);}}
function step(d){{var i=order.indexOf(cur);var j=i+d;if(j>=0&&j<order.length)show(order[j]);}}
document.addEventListener('keydown',function(e){{if(e.key==='ArrowLeft')step(-1);if(e.key==='ArrowRight')step(1);}});
show(order[0]);
</script></body></html>"""
    outpath = os.path.join(sdir, f"{name}_全部正文预览_{n}篇.html")
    open(outpath, "w", encoding="utf-8").write(out)
    return outpath, n

if __name__ == "__main__":
    args = sys.argv[1:]
    if args:
        dirs = [os.path.abspath(a) for a in args]
    else:
        dirs = find_series_dirs()
    for d in dirs:
        r = build(d)
        if r:
            print(f"✅ {r[0].replace(ROOT+os.sep,'')}  ({r[1]}篇)")
        else:
            print("⚠️ 无文章:", d)
