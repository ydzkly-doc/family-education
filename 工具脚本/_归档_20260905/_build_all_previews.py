# -*- coding: utf-8 -*-
"""通用：为指定系列的 公众号文章/ 目录生成「全部正文预览」单文件。
自动扫描 发布包_第X篇* 文件夹，取其中的 正文.html（优先 正文_第X篇*.html，
否则裸 正文.html；跳过 *说教版备份*），按篇号排序合并。"""
import os, re, sys

def extract_body(path):
    with open(path, "r", encoding="utf-8") as f:
        txt = f.read()
    m = re.search(r"<body[^>]*>(.*?)</body>", txt, re.S | re.I)
    inner = m.group(1) if m else txt
    inner = re.sub(r"<script.*?</script>", "", inner, flags=re.S | re.I)
    return inner.strip()

def build(series_dir, series_name):
    gz = os.path.join(series_dir, "公众号文章")
    if not os.path.isdir(gz):
        print("  [跳过] 无 公众号文章 目录:", gz); return
    # 收集发布包
    packs = []
    for name in os.listdir(gz):
        p = os.path.join(gz, name)
        if os.path.isdir(p) and name.startswith("发布包_"):
            m = re.search(r"第(\d+)篇", name)
            num = int(m.group(1)) if m else 999
            topic = re.sub(r"^发布包_第\d+篇_?", "", name) or ("第%d篇" % num)
            packs.append((num, topic, p, name))
    packs.sort(key=lambda x: x[0])
    if not packs:
        print("  [跳过] 无发布包:", gz); return

    articles = []
    for num, topic, p, folder in packs:
        # 找正文：优先 正文_第X篇*.html（非备份），否则裸 正文.html
        cand = []
        for fn in os.listdir(p):
            if not fn.endswith(".html"): continue
            if "说教版备份" in fn or "备份" in fn: continue
            if fn.startswith("正文"):
                cand.append(fn)
        # 裸 正文.html 优先（它是发布用正式稿）；否则取 正文_第X篇*.html
        formal = None
        if "正文.html" in cand:
            formal = "正文.html"
        elif cand:
            formal = sorted(cand)[0]
        if not formal:
            print("  [警告] 缺正文:", folder); continue
        articles.append((num, topic, os.path.join(p, formal)))

    n = len(articles)
    bodies, nav = [], []
    for num, topic, path in articles:
        body = extract_body(path)
        bodies.append("<section class='art' id='art%d'>\n%s\n</section>" % (num, body))
        nav.append('<button class="navbtn" data-target="art%d" onclick="go(%d)">'
                   '<span class="n">%d</span><span class="t">%s</span></button>'
                   % (num, num, num, topic))

    topics_js = ",".join('%d:"%s"' % (num, topic) for num, topic, _ in articles)
    tpl = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>__NAME__ · 全部正文顺序预览（共__N__篇）</title>
<style>
  *{box-sizing:border-box;}
  body{margin:0;font-family:-apple-system,"Microsoft YaHei",sans-serif;background:#f2f3f5;color:#222;}
  .topbar{position:sticky;top:0;z-index:99;background:#fff;border-bottom:1px solid #e3e3e3;box-shadow:0 2px 8px rgba(0,0,0,.05);}
  .topbar h1{font-size:16px;margin:0;padding:12px 16px 6px;color:#333;}
  .nav{display:flex;flex-wrap:wrap;gap:6px;padding:6px 16px 10px;}
  .navbtn{display:flex;align-items:center;gap:6px;border:1px solid #d9d9d9;background:#fafafa;color:#555;border-radius:18px;padding:5px 12px;font-size:13px;cursor:pointer;transition:all .15s;}
  .navbtn .n{display:inline-flex;align-items:center;justify-content:center;width:20px;height:20px;border-radius:50%;background:#e8e8e8;color:#666;font-size:12px;font-weight:600;}
  .navbtn:hover{border-color:#c98a5a;color:#c98a5a;}
  .navbtn.active{background:#c98a5a;border-color:#c98a5a;color:#fff;}
  .navbtn.active .n{background:#fff;color:#c98a5a;}
  .pager{display:flex;justify-content:space-between;align-items:center;padding:8px 16px;border-top:1px solid #f0f0f0;}
  .pager button{border:none;background:#c98a5a;color:#fff;border-radius:6px;padding:7px 16px;font-size:14px;cursor:pointer;}
  .pager button:disabled{background:#ddd;cursor:not-allowed;}
  .pager .cur{font-size:14px;color:#666;}
  .wrap{max-width:720px;margin:0 auto;padding:18px 12px 60px;}
  .art{display:none;background:#fff;border-radius:10px;padding:8px 4px;box-shadow:0 1px 6px rgba(0,0,0,.04);}
  .art.show{display:block;}
</style></head><body>
<div class="topbar">
  <h1>__NAME__ · 全部正文顺序预览（共 __N__ 篇）</h1>
  <div class="nav">__NAV__</div>
  <div class="pager">
    <button id="prevBtn" onclick="step(-1)">&#9664; 上一篇</button>
    <span class="cur" id="curLabel"></span>
    <button id="nextBtn" onclick="step(1)">下一篇 &#9654;</button>
  </div>
</div>
<div class="wrap">__BODY__</div>
<script>
  var total=__N__, cur=1;
  var topics={__TOPICS__};
  function render(){
    for(var i=1;i<=total;i++){
      var s=document.getElementById('art'+i);
      if(s) s.className='art'+(i===cur?' show':'');
      var b=document.querySelector('.navbtn[data-target="art'+i+'"]');
      if(b) b.classList.toggle('active',i===cur);
    }
    document.getElementById('curLabel').textContent='第 '+cur+' 篇 / 共 '+total+' 篇 · '+(topics[cur]||'');
    document.getElementById('prevBtn').disabled=(cur===1);
    document.getElementById('nextBtn').disabled=(cur===total);
    window.scrollTo({top:0,behavior:'smooth'});
  }
  function go(n){cur=n;render();}
  function step(d){cur=Math.min(total,Math.max(1,cur+d));render();}
  document.addEventListener('keydown',function(e){
    if(e.key==='ArrowLeft')step(-1);
    if(e.key==='ArrowRight')step(1);
  });
  render();
</script></body></html>"""
    out = (tpl.replace("__NAME__", series_name).replace("__N__", str(n))
              .replace("__NAV__", "\n".join(nav)).replace("__BODY__", "\n".join(bodies))
              .replace("__TOPICS__", topics_js))
    dest = os.path.join(gz, "%s_全部正文预览_%d篇.html" % (series_name, n))
    with open(dest, "w", encoding="utf-8") as f:
        f.write(out)
    print("  [OK] %s -> %s (%.0f KB, %d 篇)" %
          (series_name, os.path.basename(dest), os.path.getsize(dest)/1024, n))

if __name__ == "__main__":
    root = r"D:\个人资料\家庭教育"
    targets = [
        ("为什么学生不喜欢上学", "为什么学生不喜欢上学"),
        ("孩子不上学了怎么办", "孩子不上学了怎么办"),
        ("父母做到这点孩子会有惊人改变", "父母做到这点孩子会有惊人改变"),
    ]
    for folder, name in targets:
        print("处理:", name)
        build(os.path.join(root, folder), name)
