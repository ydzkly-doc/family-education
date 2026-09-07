# -*- coding: utf-8 -*-
import re
f=r"D:/个人资料/家庭教育/王金海讲书/爱的五种语言/公众号文章/发布包_第1篇_总纲_无效付出/正文_第1篇_我把工资全交了她却说我不爱家.html"
h=open(f,encoding="utf-8").read()
print("len:",len(h))
print("data-page-node-id:", h.count("data-page-node-id"))
print("data-* 总数:", len(re.findall(r'\s*data-[a-zA-Z0-9\-]+=',h)))
print("td/section/th 带color:", len(re.findall(r'<(?:td|section|th)\b[^>]*\bcolor:',h)))
print("div 带color:", len(re.findall(r'<div\b[^>]*\bcolor:',h)))
print("重复style:", len(re.findall(r'style="[^"]*"\s+style="',h)))
print("<img>:",len(re.findall(r'<img',h))," class=:",len(re.findall(r'class=',h)),
      " <style块:",len(re.findall(r'<style',h))," <div>:",len(re.findall(r'<div',h)),
      " <ul>:",len(re.findall(r'<ul',h))," <h2>:",len(re.findall(r'<h2',h)))
i=h.find("<body")
print("\n===== body 头部 1400 字 =====")
print(h[i:i+1400])
