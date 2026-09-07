# -*- coding: utf-8 -*-
import re
f=r"D:/个人资料/家庭教育/王金海讲书/爱的五种语言/公众号文章/发布包_第1篇_总纲_无效付出/正文_第1篇_我把工资全交了她却说我不爱家.html"
h=open(f,encoding="utf-8").read()
i=h.find("<body")
print("===== body 头部 1100 字 =====")
print(h[i:i+1100])
print("\n===== 规范检查 =====")
print("data-page-node-id:",h.count("data-page-node-id")," data-*:",len(re.findall(r'data-[a-zA-Z0-9\-]+=',h)))
print("td/section/th 带color:",len(re.findall(r'<(?:td|section|th)\b[^>]*\bcolor:',h)))
print("div:",len(re.findall(r'<div',h))," <p>:",len(re.findall(r'<p\b',h)))
print("img:",len(re.findall(r'<img',h))," class:",len(re.findall(r'class=',h))," style块:",len(re.findall(r'<style',h))," ul:",len(re.findall(r'<ul',h))," h2:",len(re.findall(r'<h2',h)))
for t in ("table","tr","td","section","p","span","b","strong"):
    d=len(re.findall(rf'<{t}\b',h))-len(re.findall(rf'</{t}>',h))
    if d: print("  ⚠️ 不平衡",t,d)
print("配平检查完成")
