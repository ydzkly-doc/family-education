# -*- coding: utf-8 -*-
"""合并微习惯各发布包正文为单文件预览页：导航目录 + 胶囊 + 上/下一篇 + 键盘翻页。
   系列增删篇后直接重跑本脚本即可（自动扫描 发布包_第* 目录）。"""
import re, glob, os
base = os.path.dirname(os.path.abspath(__file__))
files = sorted(glob.glob(os.path.join(base, "发布包_第*", "正文_第*.html")))

# 篇号 -> (短主题, 导航标题)；新增篇在此补一行即可
meta = {
    1: ("启动难", "书房那堆没拆膜的书，治好了我年年立flag的毛病"),
    2: ("动力意志力", "发完朋友圈就泄劲？你的意志力早被5件事掏空了"),
    3: ("定微习惯", "把目标定到“说出来都脸红”，反而更容易做到"),
    4: ("四个机关", "习惯不用硬坚持，会自己转起来——只差4个小机关"),
    5: ("用到孩子", "我没催15岁儿子学习，只把“练5遍”改成“5个一遍”"),
}
MAIN="#b07d3a"; DEEP="#8a6530"; PINK="#f0e2c6"
bodies=[]; toc=[]; chips=[]
n=len(files)
for i,f in enumerate(files,1):
    s=open(f,encoding='utf-8').read()
    b=re.search(r"<body[^>]*>(.*)</body>", s, re.S).group(1)
    topic, title = meta.get(i, ("第%d篇"%i,"第%d篇"%i))
    bodies.append('<section class="art" id="art%d" style="%s">%s</section>'%(
        i, ("" if i==1 else "display:none;"), b))
    toc.append(
      '<div class="tocrow" id="toc%d" onclick="go(%d)" style="padding:10px 12px;border-radius:8px;cursor:pointer;margin:4px 0;%s">'
      '<span style="display:inline-block;min-width:64px;font-weight:bold;color:%s;">第%d篇</span>'
      '<span style="color:%s;font-size:13px;margin-right:8px;">[%s]</span>'
      '<span style="color:#4a4038;font-size:14px;">%s</span></div>'
      %(i,i,("background:%s;"%PINK if i==1 else ""),MAIN,i,MAIN,topic,title))
    chips.append('<button onclick="go(%d)" id="nav%d" style="margin:4px;padding:7px 13px;border-radius:16px;border:1px solid %s;cursor:pointer;font-size:14px;%s">%d</button>'%(
        i,i,MAIN,("background:%s;color:#fff;"%MAIN if i==1 else "background:#fff;color:%s;"%MAIN),i))

html='''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>微习惯·全部正文预览</title></head>
<body style="margin:0;background:#efe9e0;font-family:'Microsoft YaHei',sans-serif;">
<div style="position:sticky;top:0;z-index:20;background:#fff;box-shadow:0 2px 8px rgba(0,0,0,.12);">
  <div style="max-width:720px;margin:0 auto;padding:12px 16px;">
    <div style="text-align:center;font-weight:bold;color:@@DEEP@@;font-size:17px;margin-bottom:4px;">《微习惯》· 全部正文预览（共 @@N@@ 篇）</div>
    <div style="text-align:center;color:#9a8f70;font-size:13px;margin-bottom:8px;">点目录跳转 · 底部“上/下一篇” · 键盘 ← → 翻页</div>
    <div style="text-align:center;" id="chips">@@CHIPS@@</div>
    <details style="margin-top:8px;background:#fffdf9;border:1px solid @@PINK@@;border-radius:8px;padding:6px 12px;">
      <summary style="cursor:pointer;color:@@DEEP@@;font-weight:bold;font-size:14px;padding:4px 0;">📑 全篇导航目录（点击跳转）</summary>
      <div style="margin-top:6px;">@@TOC@@</div>
    </details>
    <div id="pos" style="text-align:center;margin-top:8px;color:@@DEEP@@;font-weight:bold;font-size:14px;"></div>
  </div>
</div>
@@BODY@@
<div style="text-align:center;padding:24px;">
<button onclick="prev()" style="margin:4px;padding:10px 22px;border-radius:18px;border:1px solid @@MAIN@@;background:#fff;color:@@MAIN@@;cursor:pointer;font-size:15px;">◀ 上一篇</button>
<span style="color:#9a8f70;margin:0 12px;" id="pos2"></span>
<button onclick="next()" style="margin:4px;padding:10px 22px;border-radius:18px;border:1px solid @@MAIN@@;background:@@MAIN@@;color:#fff;cursor:pointer;font-size:15px;">下一篇 ▶</button>
</div>
<script>
var n=@@N@@,cur=1;
function render(){
  for(var i=1;i<=n;i++){
    var a=document.getElementById('art'+i); if(a) a.style.display=(i==cur)?'':'none';
    var b=document.getElementById('nav'+i);
    if(b){ b.style.background=(i==cur)?'@@MAIN@@':'#fff'; b.style.color=(i==cur)?'#fff':'@@MAIN@@'; }
    var t=document.getElementById('toc'+i);
    if(t){ t.style.background=(i==cur)?'@@PINK@@':'transparent'; }
  }
  var label='第 '+cur+' 篇 / 共 '+n+' 篇';
  document.getElementById('pos').innerText=label;
  document.getElementById('pos2').innerText=label;
}
function go(i){cur=i;render();window.scrollTo({top:0,behavior:'smooth'});}
function next(){if(cur<n)go(cur+1);}
function prev(){if(cur>1)go(cur-1);}
document.addEventListener('keydown',function(e){
  if(e.key=='ArrowRight'){next();} if(e.key=='ArrowLeft'){prev();}
});
render();
</script>
</body></html>'''
html=html.replace("@@MAIN@@",MAIN).replace("@@DEEP@@",DEEP).replace("@@PINK@@",PINK)
html=html.replace("@@CHIPS@@","".join(chips)).replace("@@TOC@@","".join(toc))
html=html.replace("@@BODY@@","".join(bodies)).replace("@@N@@",str(n))
out=os.path.join(base,"微习惯_全部正文预览_%d篇.html"%n)
open(out,"w",encoding="utf-8").write(html)
print("written:",os.path.basename(out),"articles:",n)
