# -*- coding: utf-8 -*-
"""通用：为指定系列生成带【全篇导航目录】的合并预览页。"""
import re, glob, os

def build(series_dir, series_name, main, deep, light, out_name, meta):
    base = series_dir
    # 每个发布包目录取正式正文 html（排除"备份"/"预览"）
    packs = {}
    for f in glob.glob(os.path.join(base, "发布包_第*", "*.html")):
        if "备份" in f or "预览" in f: continue
        d = os.path.dirname(f)
        m = re.search(r'第(\d+)篇', os.path.basename(d))
        n = int(m.group(1))
        packs.setdefault(n, f)
    order = sorted(packs)
    bodies=[]; toc=[]; chips=[]
    for idx, n in enumerate(order):
        f = packs[n]
        s = open(f, encoding='utf-8').read()
        b = re.search(r"<body[^>]*>(.*)</body>", s, re.S).group(1)
        topic, title = meta.get(n, ("第%d篇"%n, "第%d篇"%n))
        bodies.append('<section class="art" id="art%d" style="%s">%s</section>'%(
            idx+1, ("" if idx==0 else "display:none;"), b))
        toc.append(
          '<div id="toc%d" onclick="go(%d)" style="padding:10px 12px;border-radius:8px;cursor:pointer;margin:4px 0;%s">'
          '<span style="display:inline-block;min-width:56px;font-weight:bold;color:%s;">第%d篇</span>'
          '<span style="color:%s;font-size:13px;margin-right:8px;">[%s]</span>'
          '<span style="color:#4a4038;font-size:14px;">%s</span></div>'
          %(idx+1, idx+1, ("background:%s;"%light if idx==0 else ""), main, n, main, topic, title))
        chips.append('<button onclick="go(%d)" id="nav%d" style="margin:4px;padding:7px 13px;border-radius:16px;border:1px solid %s;cursor:pointer;font-size:14px;%s">%d</button>'%(
            idx+1, idx+1, main, ("background:%s;color:#fff;"%main if idx==0 else "background:#fff;color:%s;"%main), n))
    N=len(order)
    T = '''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>@NAME@·全部正文预览·@N@篇</title></head>
<body style="margin:0;background:#efe9e2;font-family:'Microsoft YaHei',sans-serif;">
<div style="position:sticky;top:0;z-index:20;background:#fff;box-shadow:0 2px 8px rgba(0,0,0,.12);">
  <div style="max-width:720px;margin:0 auto;padding:12px 16px;">
    <div style="text-align:center;font-weight:bold;color:@DEEP@;font-size:17px;margin-bottom:4px;">《@NAME@》· 全部正文预览（共 @N@ 篇）</div>
    <div style="text-align:center;color:#9a8f70;font-size:13px;margin-bottom:8px;">点目录跳转 · 底部“上/下一篇” · 键盘 ← → 翻页</div>
    <div style="text-align:center;" id="chips">@CHIPS@</div>
    <details style="margin-top:8px;background:#fffdf9;border:1px solid @LIGHT@;border-radius:8px;padding:6px 12px;">
      <summary style="cursor:pointer;color:@DEEP@;font-weight:bold;font-size:14px;padding:4px 0;">📑 全篇导航目录（点击跳转）</summary>
      <div style="margin-top:6px;">@TOC@</div>
    </details>
    <div id="pos" style="text-align:center;margin-top:8px;color:@DEEP@;font-weight:bold;font-size:14px;"></div>
  </div>
</div>
@BODY@
<div style="text-align:center;padding:24px;">
<button onclick="prev()" style="margin:4px;padding:10px 22px;border-radius:18px;border:1px solid @MAIN@;background:#fff;color:@MAIN@;cursor:pointer;font-size:15px;">◀ 上一篇</button>
<span style="color:#9a8f70;margin:0 12px;" id="pos2"></span>
<button onclick="next()" style="margin:4px;padding:10px 22px;border-radius:18px;border:1px solid @MAIN@;background:@MAIN@;color:#fff;cursor:pointer;font-size:15px;">下一篇 ▶</button>
</div>
<script>
var n=@N@,cur=1;
function render(){for(var i=1;i<=n;i++){
  document.getElementById('art'+i).style.display=(i==cur)?'':'none';
  var b=document.getElementById('nav'+i);
  b.style.background=(i==cur)?'@MAIN@':'#fff';b.style.color=(i==cur)?'#fff':'@MAIN@';
  var t=document.getElementById('toc'+i);
  t.style.background=(i==cur)?'@LIGHT@':'transparent';}
  var label='第 '+cur+' 篇 / 共 '+n+' 篇';
  document.getElementById('pos').innerText=label;document.getElementById('pos2').innerText=label;}
function go(i){cur=i;render();window.scrollTo({top:0,behavior:'smooth'});}
function next(){if(cur<n)go(cur+1);}function prev(){if(cur>1)go(cur-1);}
document.addEventListener('keydown',function(e){if(e.key=='ArrowRight')next();if(e.key=='ArrowLeft')prev();});
render();
</script></body></html>'''
    T = (T.replace("@MAIN@",main).replace("@DEEP@",deep).replace("@LIGHT@",light)
           .replace("@NAME@",series_name).replace("@N@",str(N))
           .replace("@CHIPS@","".join(chips)).replace("@TOC@","".join(toc))
           .replace("@BODY@","".join(bodies)))
    out = os.path.join(base, out_name)
    open(out,"w",encoding="utf-8").write(T)
    print("written:",out,"篇数",N)

root = r"D:/个人资料/家庭教育"

build(os.path.join(root,"为什么学生不喜欢上学/公众号文章"),
      "为什么学生不喜欢上学","#3f6f6a","#2f5753","#d6e6e3",
      "为什么学生不喜欢上学_全部正文预览_8篇.html",
      {1:("5个学习真相","孩子不是不爱学习，是大脑本来就“懒得思考”"),
       2:("30秒速览","孩子学习这件事，30秒看清5个真相"),
       3:("学习区","孩子打游戏能专注，一写作业就喊累？"),
       4:("知识先于技能","“知识网上都能搜到，何必背？”这句话正在害孩子"),
       5:("记忆真相","单词抄十遍还是忘？因为孩子手在动脑子没动"),
       6:("练习与题海","被骂多年的“题海战术”，哈佛教授说它其实是对的"),
       7:("专家思维","专家的“第六感”能不能教给孩子？答案有点残酷"),
       8:("成长型思维","孩子总说“我就是笨”？比成绩更可怕的是这句话")})

build(os.path.join(root,"孩子不上学了怎么办/公众号文章"),
      "孩子不上学了怎么办","#b06a48","#8a4f33","#f0e2d4",
      "孩子不上学了怎么办_全部正文预览_6篇.html",
      {1:("接错话","孩子说“我不想上学了”那一刻，90%父母都接错了话"),
       2:("起跑线焦虑","“别让孩子输在起跑线”是这个时代最大的骗局"),
       3:("四类高风险家庭","这四种家庭，孩子最容易辍学，希望没有你家"),
       4:("厌学四阶段","孩子厌学有四个阶段，聪明父母在前两段就拦住了"),
       5:("化情大法","孩子说“不想上学”，我忍住没讲道理，只做了四件事"),
       6:("30秒速览","30秒看懂：孩子不想上学，家长到底该怎么办")})

build(os.path.join(root,"父母做到这点孩子会有惊人改变/公众号文章"),
      "父母做到这点孩子会有惊人改变","#c8643c","#a8502c","#f6ddcf",
      "父母做到这点孩子会有惊人改变_全部正文预览_5篇.html",
      {1:("开门原理","父母改变1%，孩子改变100%"),
       2:("自动驾驶","晚上想想千条路，早上醒来走原路"),
       3:("比较与掌控","你看看人家孩子，我是为你好"),
       4:("十六字箴言","一个家最好的风水：十六字箴言"),
       5:("知道到做到","从知道到做到，隔着三步")})
