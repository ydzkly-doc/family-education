# -*- coding: utf-8 -*-
import re
def head(f,label,n=2000):
    h=open(f,encoding="utf-8").read()
    i=h.find("<body")
    seg=h[i:i+n] if i>=0 else h[:n]
    print("="*80); print(label)
    print(seg)

head(r"D:/个人资料/家庭教育/青春期30讲/公众号文章/发布包_第1篇_总纲/正文_第1篇_总纲.html",
     "【成功】青春期30讲 第1篇 body头部")
