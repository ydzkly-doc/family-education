# -*- coding: utf-8 -*-
import re
f=r"D:/个人资料/家庭教育/王金海讲书/非暴力沟通/公众号文章/发布包_第1篇_总纲_三天没说话/正文_第1篇_我吼完孩子那句你懂什么他三天没跟我说话.html"
h=open(f,encoding="utf-8").read()
i=h.find("<body")
print("===== 头部 900 字 =====")
print(h[i:i+900])
print("\n===== 规范检查 =====")
print("data-page-node-id:", h.count("data-page-node-id"))
print("td/section/th 带color:", len(re.findall(r'<(?:td|section|th)\b[^>]*\bcolor:',h)))
print("重复style:", len(re.findall(r'style="[^"]*"\s+style="',h)))
print("<img>:",len(re.findall(r'<img',h))," class=:",len(re.findall(r'class=',h)),
      " <style块:",len(re.findall(r'<style',h))," <div>:",len(re.findall(r'<div',h)),
      " <ul>:",len(re.findall(r'<ul',h))," <h2>:",len(re.findall(r'<h2',h)))
for t in ("table","tr","td","section","p","span","b","strong"):
    d=len(re.findall(rf'<{t}\b',h))-len(re.findall(rf'</{t}>',h))
    if d: print("  ⚠️ 不平衡",t,d)
print("标签配平检查完成")
