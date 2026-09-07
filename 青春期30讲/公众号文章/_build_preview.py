# -*- coding: utf-8 -*-
import os, re, html

BASE = os.path.dirname(os.path.abspath(__file__))

# 篇号 -> (文件夹名, 正文文件名, 短主题)
articles = [
    (1,  "发布包_第1篇_总纲",      "正文_第1篇_总纲.html",      "总纲"),
    (2,  "发布包_第2篇_沟通入门",  "正文_第2篇_沟通入门.html",  "沟通入门"),
    (3,  "发布包_第3篇_批评表扬",  "正文_第3篇_批评表扬.html",  "批评表扬"),
    (4,  "发布包_第4篇_叛逆情绪",  "正文_第4篇_叛逆情绪.html",  "叛逆情绪"),
    (5,  "发布包_第5篇_校园关系",  "正文_第5篇_校园关系.html",  "校园关系"),
    (6,  "发布包_第6篇_学习动力",  "正文_第6篇_学习动力.html",  "学习动力"),
    (7,  "发布包_第7篇_手机游戏",  "正文_第7篇_手机游戏.html",  "手机游戏"),
    (8,  "发布包_第8篇_早恋性教育","正文_第8篇_早恋性教育.html","早恋性教育"),
    (9,  "发布包_第9篇_自卑抗挫",  "正文_第9篇_自卑抗挫.html",  "自卑抗挫"),
    (10, "发布包_第10篇_爱美攀比", "正文_第10篇_爱美攀比.html", "爱美攀比"),
    (11, "发布包_第11篇_金钱观",   "正文_第11篇_金钱观.html",   "金钱观"),
    (12, "发布包_第12篇_自律执行", "正文_第12篇_自律执行.html", "自律执行"),
    (13, "发布包_第13篇_规则权威", "正文_第13篇_规则权威.html", "规则权威"),
    (14, "发布包_第14篇_持久战",   "正文_第14篇_持久战.html",   "持久战"),
    (15, "发布包_第15篇_父母耐心", "正文_第15篇_父母耐心.html", "父母耐心"),
    (16, "发布包_第16篇_眼神形象", "正文_第16篇_眼神形象.html", "眼神形象"),
    (17, "发布包_第17篇_自我修行", "正文_第17篇_自我修行.html", "自我修行"),
    (18, "发布包_第18篇_收官合集", "正文_第18篇_收官合集.html", "收官合集"),
]

def extract_body(path):
    with open(path, "r", encoding="utf-8") as f:
        txt = f.read()
    m = re.search(r"<body[^>]*>(.*?)</body>", txt, re.S | re.I)
    inner = m.group(1) if m else txt
    # 去掉可能的 script
    inner = re.sub(r"<script.*?</script>", "", inner, flags=re.S | re.I)
    return inner.strip()

bodies = []
nav_buttons = []
for idx, (num, folder, fname, topic) in enumerate(articles):
    path = os.path.join(BASE, folder, fname)
    if not os.path.exists(path):
        bodies.append(f"<section class='art' id='art{num}'><p style='padding:40px;color:#c00'>缺少文件：{fname}</p></section>")
    else:
        body = extract_body(path)
        bodies.append(f"<section class='art' id='art{num}'>\n{body}\n</section>")
    nav_buttons.append(
        f'<button class="navbtn" data-target="art{num}" onclick="go({num})">'
        f'<span class="n">{num}</span><span class="t">{topic}</span></button>'
    )

out = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>青春期30讲 · 全部正文顺序预览（共18篇）</title>
<style>
  * { box-sizing: border-box; }
  body { margin:0; font-family: -apple-system, "Microsoft YaHei", sans-serif; background:#f2f3f5; color:#222; }
  .topbar { position:sticky; top:0; z-index:99; background:#fff; border-bottom:1px solid #e3e3e3; box-shadow:0 2px 8px rgba(0,0,0,.05); }
  .topbar h1 { font-size:16px; margin:0; padding:12px 16px 6px; color:#333; }
  .nav { display:flex; flex-wrap:wrap; gap:6px; padding:6px 16px 10px; }
  .navbtn { display:flex; align-items:center; gap:6px; border:1px solid #d9d9d9; background:#fafafa; color:#555;
            border-radius:18px; padding:5px 12px; font-size:13px; cursor:pointer; transition:all .15s; }
  .navbtn .n { display:inline-flex; align-items:center; justify-content:center; width:20px; height:20px; border-radius:50%;
               background:#e8e8e8; color:#666; font-size:12px; font-weight:600; }
  .navbtn:hover { border-color:#c98a5a; color:#c98a5a; }
  .navbtn.active { background:#c98a5a; border-color:#c98a5a; color:#fff; }
  .navbtn.active .n { background:#fff; color:#c98a5a; }
  .pager { display:flex; justify-content:space-between; align-items:center; padding:8px 16px; border-top:1px solid #f0f0f0; }
  .pager button { border:none; background:#c98a5a; color:#fff; border-radius:6px; padding:7px 16px; font-size:14px; cursor:pointer; }
  .pager button:disabled { background:#ddd; cursor:not-allowed; }
  .pager .cur { font-size:14px; color:#666; }
  .wrap { max-width:720px; margin:0 auto; padding:18px 12px 60px; }
  .art { display:none; background:#fff; border-radius:10px; padding:8px 4px; box-shadow:0 1px 6px rgba(0,0,0,.04); }
  .art.show { display:block; }
</style>
</head>
<body>
<div class="topbar">
  <h1>青春期30讲 · 全部正文顺序预览（共 18 篇）</h1>
  <div class="nav">
__NAV__
  </div>
  <div class="pager">
    <button id="prevBtn" onclick="step(-1)">◀ 上一篇</button>
    <span class="cur" id="curLabel"></span>
    <button id="nextBtn" onclick="step(1)">下一篇 ▶</button>
  </div>
</div>
<div class="wrap">
__BODY__
</div>
<script>
  var total = 18;
  var cur = 1;
  var topics = {__TOPICS__};
  function render(){
    for(var i=1;i<=total;i++){
      var s = document.getElementById('art'+i);
      if(s) s.className = 'art' + (i===cur?' show':'');
      var b = document.querySelector('.navbtn[data-target="art'+i+'"]');
      if(b) b.classList.toggle('active', i===cur);
    }
    document.getElementById('curLabel').textContent = '第 '+cur+' 篇 / 共 '+total+' 篇 · ' + (topics[cur]||'');
    document.getElementById('prevBtn').disabled = (cur===1);
    document.getElementById('nextBtn').disabled = (cur===total);
    window.scrollTo({top:0, behavior:'smooth'});
  }
  function go(n){ cur = n; render(); }
  function step(d){ cur = Math.min(total, Math.max(1, cur+d)); render(); }
  document.addEventListener('keydown', function(e){
    if(e.key==='ArrowLeft') step(-1);
    if(e.key==='ArrowRight') step(1);
  });
  render();
</script>
</body>
</html>
"""

topics_js = ",".join('{0}:"{1}"'.format(n, t) for n, _, _, t in articles)
out = out.replace("__NAV__", "\n".join(nav_buttons))
out = out.replace("__BODY__", "\n".join(bodies))
out = out.replace("__TOPICS__", topics_js)

dest = os.path.join(BASE, "青春期30讲_全部正文预览_18篇.html")
with open(dest, "w", encoding="utf-8") as f:
    f.write(out)
print("OK ->", dest)
print("size(KB):", round(os.path.getsize(dest)/1024, 1))
