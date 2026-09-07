# -*- coding: utf-8 -*-
import re
f=r"D:/个人资料/家庭教育/青春期30讲/公众号文章/发布包_第1篇_总纲/正文_第1篇_总纲.html"
h=open(f,encoding="utf-8").read()
print("len:",len(h))
checks={
 "data-page-node-id": h.count("data-page-node-id"),
 "data-*": len(re.findall(r'\s*data-[a-zA-Z0-9\-]+=',h)),
 "<img": len(re.findall(r'<img',h)),
 "class=": len(re.findall(r'class=',h)),
 "<style块": len(re.findall(r'<style',h)),
 "<div": len(re.findall(r'<div',h)),
 "<ul/<ol/<li": len(re.findall(r'<[uo]l|<li',h)),
 "<h1~h4": len(re.findall(r'<h[1-4]',h)),
 "<section": len(re.findall(r'<section',h)),
 "<p": len(re.findall(r'<p\b',h)),
 "<span": len(re.findall(r'<span',h)),
 "td/section/th带color": len(re.findall(r'<(?:td|section|th)\b[^>]*\bcolor:',h)),
 "重复style": len(re.findall(r'style="[^"]*"\s+style="',h)),
 "<br>": len(re.findall(r'<br\s*/?>',h)),
}
for k,v in checks.items(): print(f"  {k}: {v}")
# 白字标题块是否含br
white_br=len(re.findall(r'color:#ffffff[^>]*>[^<]*<br',h))
print("  白字块内br:",white_br)
for t in ("table","tr","td","section","p","span","b","strong"):
    d=len(re.findall(rf'<{t}\b',h))-len(re.findall(rf'</{t}>',h))
    if d: print("  ⚠️ 不平衡",t,d)
print("配平OK")
# body 底色 / 主表对齐
m=re.search(r'<body[^>]*>',h); print("\nbody:",m.group(0))
m=re.search(r'<table[^>]*width="680"[^>]*>',h); print("主表:",m.group(0)[:200] if m else "NA")
