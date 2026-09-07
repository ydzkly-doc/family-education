# -*- coding: utf-8 -*-
"""全量扫描家庭教育目录下所有公众号正文 HTML，按 A/B/C 三类问题诊断。"""
import os,re,json

ROOT=r"D:/个人资料/家庭教育"
# 只收集发布包里的"正文_*.html"（正文成稿），排除预览、备份、候选、说教版
files=[]
for dirpath,dirnames,filenames in os.walk(ROOT):
    p=dirpath.replace("\\","/")
    if "_backup" in p or "/.workbuddy" in p or "封面候选" in p or "封面" in p:
        continue
    for fn in filenames:
        if not fn.endswith(".html"): continue
        if not fn.startswith("正文_"): continue
        if "预览" in fn: continue
        files.append(os.path.join(dirpath,fn).replace("\\","/"))
files.sort()

rows=[]
for f in files:
    h=open(f,encoding="utf-8").read()
    rel=f.replace(ROOT+"/","")
    data_id=h.count("data-page-node-id")+len(re.findall(r'\s*data-[a-zA-Z0-9\-]+=',h))
    div=len(re.findall(r'<div\b',h))
    p=len(re.findall(r'<p\b',h))
    td_color=len(re.findall(r'<(?:td|section|th)\b[^>]*\bcolor:',h))
    dup=len(re.findall(r'style="[^"]*"\s+style="',h))
    img=len(re.findall(r'<img',h)); cls=len(re.findall(r'class=',h)); styleblock=len(re.findall(r'<style',h))
    ul=len(re.findall(r'<[uo]l|<li',h)); h2=len(re.findall(r'<h[1-4]',h))
    # 白字标题块内 br
    white_br=len(re.findall(r'color:\s*#(?:fff|ffffff)\b[^>]*>[^<]*<br',h))
    problems=[]
    if data_id>0: problems.append(f"A(data-id {data_id})")
    if div>0: problems.append(f"C(div {div})")
    if white_br>0: problems.append(f"C(白字br {white_br})")
    if td_color>0: problems.append(f"B(td色 {td_color})")
    if dup>0: problems.append(f"重复style {dup}")
    if img or cls or styleblock or ul or h2:
        problems.append(f"违禁[img{img}/cls{cls}/style{styleblock}/ul{ul}/h{h2}]")
    rows.append((rel, ";".join(problems) if problems else "OK", div,p,td_color,data_id))

print(f"共 {len(files)} 篇正文\n")
print(f"{'状态':<6} {'div':>3} {'p':>3} {'td色':>4} {'dataid':>6}  文件")
ok=0
for rel,prob,div,p,tdc,did in rows:
    tag="OK" if prob=="OK" else "❌"
    if prob=="OK": ok+=1
    print(f"{tag:<6} {div:>3} {p:>3} {tdc:>4} {did:>6}  {rel}")
    if prob!="OK":
        print(f"        └ {prob}")
print(f"\n合格 {ok} / {len(rows)}；待修 {len(rows)-ok}")
