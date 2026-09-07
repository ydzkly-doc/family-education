# -*- coding: utf-8 -*-
"""
v3 确定性修复：微信公众号粘贴丢色
思路：只针对 td/section/th 开标签自身带 color 的情况。
遍历其内部子节点：
  - 文本节点（含 &nbsp; 实体）若"去空白后非空"，视为裸文字 -> 用 <span style="color:xxx"> 包起来；
  - 若文本只是空白/&nbsp;（装饰竖条），不包；
  - 内部标签（p/span/b/strong/br/table...）原样透传（它们自己有色与否都不动，避免嵌套 p）。
然后从 td/section/th 的开标签 style 中移除 color（背景/内边距保留），
因为颜色已经下沉到每个裸文字的 span 上。
同时：合并同一标签重复的 style="..."。
用法: python _fix_v3.py file1.html file2.html
"""
import re, sys
from html.parser import HTMLParser

def merge_styles_in_tag(tagtext):
    styles = re.findall(r'style="([^"]*)"', tagtext)
    if len(styles) <= 1:
        return tagtext
    merged={}; order=[]
    for s in styles:
        for decl in s.split(";"):
            decl=decl.strip()
            if not decl or ":" not in decl: continue
            k,v=decl.split(":",1); k=k.strip(); v=v.strip()
            if k not in merged: order.append(k)
            merged[k]=v
    ms=";".join(f"{k}:{merged[k]}" for k in order)
    t=re.sub(r'\s*style="[^"]*"','',tagtext)
    return t[:-1]+f' style="{ms}">'

def get_color(style):
    m=re.search(r'(?:^|;)\s*color\s*:\s*(#[0-9a-fA-F]{3,6}|[a-zA-Z]+)', style)
    return m.group(1) if m else None

def del_color(style):
    parts=[p for p in style.split(";") if p.strip() and not re.match(r'\s*color\s*:',p)]
    return ";".join(p.strip() for p in parts if p.strip())

class Fixer(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.out=[]
        # 追踪栈：每个元素 dict(tag, color, depth_inner)
        # color 非 None 表示这是一个需要把裸文字包色的 td/section/th
        self.track=[]
    def _emit(self, s):
        if self.track and self.track[-1]["color"]:
            self.track[-1]["buf"].append(s)
        else:
            self.out.append(s)
    def handle_starttag(self, tag, attrs):
        full=merge_styles_in_tag(self.get_starttag_text())
        m=re.search(r'style="([^"]*)"',full)
        style=m.group(1) if m else ""
        color=get_color(style)
        if tag in ("td","section","th") and color:
            # 开始追踪；先改造开标签（去掉 color）
            new_style=del_color(style)
            if new_style:
                new_open=re.sub(r'style="[^"]*"',f'style="{new_style}"',full)
            else:
                new_open=re.sub(r'\s*style="[^"]*"','',full)
            self.track.append({"tag":tag,"color":color,"buf":[],"open":new_open,"innerdepth":0})
            return
        # 其它标签：若在追踪块内，算内层标签（原样透传进 buf），并记录深度
        if self.track and self.track[-1]["color"]:
            self.track[-1]["buf"].append(full)
            # 非自闭合的内层块/包裹标签需要配对深度（用 void 标签判断）
            if tag not in ("br","img","hr","input","meta","link","area","base","col","embed","source","track","wbr"):
                self.track[-1]["innerdepth"]+=1
            return
        self.out.append(full)
    def handle_startendtag(self, tag, attrs):
        full=merge_styles_in_tag(self.get_starttag_text())
        self._emit(full)
    def handle_endtag(self, tag):
        if self.track and self.track[-1]["color"] and self.track[-1]["tag"]==tag and self.track[-1]["innerdepth"]==0:
            # 闭合追踪块
            t=self.track.pop()
            inner=self._wrap_bare("".join(t["buf"]), t["color"])
            self.out.append(t["open"]); self.out.append(inner); self.out.append(f"</{tag}>")
            return
        if self.track and self.track[-1]["color"]:
            # 内层标签闭合
            if tag not in ("br","img","hr","input"):
                self.track[-1]["innerdepth"]-=1
            self.track[-1]["buf"].append(f"</{tag}>")
            return
        self.out.append(f"</{tag}>")
    def _wrap_bare(self, inner, color):
        # 把"顶层裸文字"包 span；但若文字位于一个自带 color 的内层标签内，则不包（避免覆盖）。
        tokens=re.split(r'(<[^>]+>)', inner)
        res=[]
        suppress=[]  # 栈：存放带 color 的内层标签名
        void={"br","img","hr","input","meta","link","area","base","col","embed","source","track","wbr"}
        for tok in tokens:
            if not tok: continue
            if tok.startswith("</"):
                tname=re.match(r'</\s*([a-zA-Z0-9]+)',tok)
                tn=tname.group(1).lower() if tname else None
                if suppress and suppress[-1]==tn:
                    suppress.pop()
                res.append(tok)
            elif tok.startswith("<"):
                tm=re.match(r'<\s*([a-zA-Z0-9]+)',tok)
                tn=tm.group(1).lower() if tm else None
                selfclosing = tok.rstrip().endswith("/>") or tn in void
                # 是否自带 color
                sm=re.search(r'style="([^"]*)"',tok)
                has_color = bool(sm and get_color(sm.group(1)))
                res.append(tok)
                if not selfclosing and has_color:
                    suppress.append(tn)
            else:
                visible=tok.replace("&nbsp;","").strip()
                if visible and not suppress:
                    res.append(f'<span style="color:{color};">{tok}</span>')
                else:
                    res.append(tok)
        return "".join(res)
    def handle_data(self, data):
        self._emit(data)
    def handle_entityref(self, name):
        self._emit(f"&{name};")
    def handle_charref(self, name):
        self._emit(f"&#{name};")

for f in sys.argv[1:]:
    h=open(f,encoding="utf-8").read()
    p=Fixer(); p.feed(h); p.close()
    res="".join(p.out)
    before=len(re.findall(r'<(?:td|section|th)\b[^>]*\bcolor:',h))
    after=len(re.findall(r'<(?:td|section|th)\b[^>]*\bcolor:',res))
    dupb=len(re.findall(r'style="[^"]*"\s+style="',h))
    dupa=len(re.findall(r'style="[^"]*"\s+style="',res))
    # 标签平衡粗检
    def bal(s,t): return len(re.findall(rf'<{t}\b',s))-len(re.findall(rf'</{t}>',s))
    bals={t:bal(res,t) for t in ("table","tr","td","section","p","span","b")}
    open(f,"w",encoding="utf-8").write(res)
    print(f"{f}\n  td/sec/th带color {before}->{after}; 重复style {dupb}->{dupa}; 平衡差 {bals}; len {len(h)}->{len(res)}")
