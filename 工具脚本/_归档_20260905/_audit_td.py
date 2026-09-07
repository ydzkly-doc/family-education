# -*- coding: utf-8 -*-
import re
f=r"D:/个人资料/家庭教育/青春期30讲/公众号文章/发布包_第1篇_总纲/正文_第1篇_总纲.html"
h=open(f,encoding="utf-8").read()
# 逐个看带color的td，判断内部文字是否被带色的p/span/b包裹
for idx,m in enumerate(re.finditer(r'<td\b[^>]*\bcolor:([^;"]+)[^>]*>',h)):
    color=m.group(1)
    # 取该td到对应</td>的内容（简单截取到下一个</td>）
    start=m.end()
    end=h.find('</td>',start)
    inner=h[start:end]
    # 内部是否有带color的文字承载标签
    inner_colored=bool(re.search(r'<(?:p|span|b|strong)\b[^>]*\bcolor:',inner))
    # 内部是否有裸文字（去掉标签后有字）
    bare=re.sub(r'<[^>]+>','',inner).replace('&nbsp;','').strip()
    has_bare=bool(bare)
    # 是否装饰条（width:6px 之类）
    deco = 'width:6px' in m.group(0) or len(bare)==0
    print(f"[{idx}] td色={color.strip()} 内部有带色标签={inner_colored} 有裸文字={has_bare} 装饰={deco}")
    if has_bare and not inner_colored:
        print("    ⚠️ 裸文字且内部无带色标签:", bare[:40])
