# -*- coding: utf-8 -*-
"""合并各发布包正文为单文件预览页：顶部统一导航目录(标题+主题) + 胶囊 + 上/下一篇 + 键盘翻页。"""
import re, glob, os
base = os.path.dirname(os.path.abspath(__file__))
files = sorted(glob.glob(os.path.join(base, "发布包_第*", "*.html")))

# 篇号 -> (导航短主题, 文章主标题) 用于目录
meta = {
    1: ("总纲·无效付出", "我把工资全交了，她却说我不爱这个家"),
    2: ("肯定的言词",   "“你就不能说句好听的？”——我们家最缺的不是钱"),
    3: ("精心的时刻",   "同床共枕十年，我们却像两个合租的室友"),
    4: ("接受礼物",     "她不是物质，她只是想确认“你心里有我”"),
    5: ("服务的行动",   "“我来做”，是婚姻里最动听的一句情话"),
    6: ("身体的接触",   "孩子摔门那晚，我才懂这个家多久没“碰”过了"),
}
bodies=[]; toc=[]; chips=[]
for i,f in enumerate(files,1):
    s=open(f,encoding='utf-8').read()
    b=re.search(r"<body[^>]*>(.*)</body>", s, re.S).group(1)
    topic, title = meta.get(i, ("第%d篇"%i,"第%d篇"%i))
    bodies.append('<section class="art" id="art%d" style="%s">%s</section>'%(
        i, ("" if i==1 else "display:none;"), b))
    # 目录行
    toc.append(
      '<div class="tocrow" id="toc%d" onclick="go(%d)" style="padding:10px 12px;border-radius:8px;cursor:pointer;margin:4px 0;%s">'
      '<span style="display:inline-block;min-width:64px;font-weight:bold;color:#a85f66;">第%d篇</span>'
      '<span style="color:#c4797e;font-size:13px;margin-right:8px;">[%s]</span>'
      '<span style="color:#4a3f42;font-size:14px;">%s</span></div>'
      %(i,i,("background:#fbeeef;" if i==1 else ""),i,topic,title))
    # 胶囊
    chips.append('<button onclick="go(%d)" id="nav%d" style="margin:4px;padding:7px 13px;border-radius:16px;border:1px solid #c4797e;cursor:pointer;font-size:14px;%s">%d</button>'%(
        i,i,("background:#c4797e;color:#fff;" if i==1 else "background:#fff;color:#c4797e;"),i))

html='''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>爱的五种语言·全部正文预览·6篇</title></head>
<body style="margin:0;background:#ece5e3;font-family:'Microsoft YaHei',sans-serif;">

<div style="position:sticky;top:0;z-index:20;background:#fff;box-shadow:0 2px 8px rgba(0,0,0,.12);">
  <div style="max-width:720px;margin:0 auto;padding:12px 16px;">
    <div style="text-align:center;font-weight:bold;color:#a85f66;font-size:17px;margin-bottom:4px;">《爱的五种语言》· 全部正文预览（共 6 篇）</div>
    <div style="text-align:center;color:#9c8286;font-size:13px;margin-bottom:8px;">点目录跳转 · 底部“上/下一篇” · 键盘 ← → 翻页</div>
    <div style="text-align:center;" id="chips">@@CHIPS@@</div>
    <details style="margin-top:8px;background:#fdfafb;border:1px solid #f0d9da;border-radius:8px;padding:6px 12px;">
      <summary style="cursor:pointer;color:#a85f66;font-weight:bold;font-size:14px;padding:4px 0;">📑 全篇导航目录（点击跳转）</summary>
      <div style="margin-top:6px;">@@TOC@@</div>
    </details>
    <div id="pos" style="text-align:center;margin-top:8px;color:#a85f66;font-weight:bold;font-size:14px;"></div>
  </div>
</div>

@@BODY@@

<div style="text-align:center;padding:24px;">
<button onclick="prev()" style="margin:4px;padding:10px 22px;border-radius:18px;border:1px solid #c4797e;background:#fff;color:#c4797e;cursor:pointer;font-size:15px;">◀ 上一篇</button>
<span style="color:#9c8286;margin:0 12px;" id="pos2"></span>
<button onclick="next()" style="margin:4px;padding:10px 22px;border-radius:18px;border:1px solid #c4797e;background:#c4797e;color:#fff;cursor:pointer;font-size:15px;">下一篇 ▶</button>
</div>

<script>
var n=@@N@@,cur=1;
function render(){
  for(var i=1;i<=n;i++){
    document.getElementById('art'+i).style.display=(i==cur)?'':'none';
    var b=document.getElementById('nav'+i);
    b.style.background=(i==cur)?'#c4797e':'#fff'; b.style.color=(i==cur)?'#fff':'#c4797e';
    var t=document.getElementById('toc'+i);
    t.style.background=(i==cur)?'#fbeeef':'transparent';
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
html=html.replace("@@CHIPS@@","".join(chips)).replace("@@TOC@@","".join(toc))
html=html.replace("@@BODY@@","".join(bodies)).replace("@@N@@",str(len(files)))
out=os.path.join(base,"爱的五种语言_全部正文预览_6篇.html")
open(out,"w",encoding="utf-8").write(html)
print("written:",out,"articles:",len(files))
