# -*- coding: utf-8 -*-
import re
f=r"D:/个人资料/家庭教育/王金海讲书/非暴力沟通/公众号文章/发布包_第1篇_总纲_三天没说话/正文_第1篇_我吼完孩子那句你懂什么他三天没跟我说话.html"
h=open(f,encoding="utf-8").read()
i=h.find("<body")
print(h[i:i+2200])
