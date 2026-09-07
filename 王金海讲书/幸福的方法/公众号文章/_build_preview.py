# -*- coding: utf-8 -*-
"""合并各发布包正文为单文件预览页：顶部统一导航目录(标题+主题) + 胶囊 + 上/下一篇 + 键盘翻页。"""
import re, glob, os
base = os.path.dirname(os.path.abspath(__file__))
files = sorted(glob.glob(os.path.join(base, "发布包_第*", "*.html")))

meta = {
    1: ("总纲", "儿子摔门：“你根本不爱我，你只想要个成绩好的我”"),
    2: ("当下幸福", "“等孩子考上大学就好了”，这句话骗了我们半辈子"),
    3: ("专注与心流", "孩子打游戏能专注，一写作业就喊累？真相不在“懒”"),
    4: ("优秀与快乐", "又想孩子优秀，又想他快乐，真的只能二选一吗"),
    5: ("父母的光", "你脸上有没有光，孩子一眼就知道"),
    6: ("幸福可练", "幸福不是等来的，是练出来的：我家试了 5 件小事"),
}
MAIN="#a47a3a"; DEEP="#8a6530"; PINK="#f0e2c6"
bodies=[]; toc=[]; chips=[]
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

html='''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>幸福的方法·全部正文预览·6篇</title></head>
<body style="margin:0;background:#efe9e0;font-family:'Microsoft YaHei',sans-serif;">
<div style="position:sticky;top:0;z-index:20;background:#fff;box-shadow:0 2px 8px rgba(0,0,0,.12);">
  <div style="max-width:720px;margin:0 auto;padding:12px 16px;">
    <div style="text-align:center;font-weight:bold;color:@@DEEP@@;font-size:17px;margin-bottom:4px;">《幸福的方法》· 全部正文预览（共 6 篇）</div>
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
    document.getElementById('art'+i).style.display=(i==cur)?'':'none';
    var b=document.getElementById('nav'+i);
    b.style.background=(i==cur)?'@@MAIN@@':'#fff'; b.style.color=(i==cur)?'#fff':'@@MAIN@@';
    var t=document.getElementById('toc'+i);
    t.style.background=(i==cur)?'@@PINK@@':'transparent';
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
html=html.replace("@@BODY@@","".join(bodies)).replace("@@N@@",str(len(files)))
out=os.path.join(base,"幸福的方法_全部正文预览_6篇.html")
open(out,"w",encoding="utf-8").write(html)
print("written:",out,"articles:",len(files))
