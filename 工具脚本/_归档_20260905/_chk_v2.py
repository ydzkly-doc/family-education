import re
FILES=[
 r"D:/个人资料/家庭教育/孩子不上学了怎么办/公众号文章/发布包_第1篇_接错话/正文_第1篇_接错话.html",
 r"D:/个人资料/家庭教育/王金海讲书/非暴力沟通/公众号文章/发布包_第1篇_总纲_三天没说话/正文_第1篇_我吼完孩子那句你懂什么他三天没跟我说话.html",
]
for f in FILES:
    h=open(f,encoding='utf-8').read()
    print("===",f.split('/')[-1])
    for t in ['table','tr','td','p','span','b','strong','section','h1']:
        o=len(re.findall(r'<%s[ >]'%t,h)); c=len(re.findall(r'</%s>'%t,h))
        if o!=c: print(f"  !! {t}: {o}/{c}")
    print("  table",h.count('<table'),h.count('</table>'),
          " p",len(re.findall(r'<p[ >]',h)),h.count('</p>'),
          " td",len(re.findall(r'<td[ >]',h)),h.count('</td>'),
          " section",len(re.findall(r'<section[ >]',h)),h.count('</section>'))
    # 无 color 的 p 数量（正文 p 应有色）
    ps=re.findall(r'<p\s[^>]*>|<p>',h)
    nop=[p for p in ps if 'color:' not in p]
    print("  无color的<p>开标签数:",len(nop))
    for p in nop[:5]: print("    ",p[:120])
