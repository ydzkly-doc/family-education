# -*- coding: utf-8 -*-
"""
微信公众号 HTML 一键规范化流水线（幂等，可重复跑）。
顺序：A 剥 data-* → C div转p + 白字标题拆br → B td/section/th 颜色下沉到 span
用法：
  python wx_html_fix.py <file.html> [more...]      # 修复
  python wx_html_fix.py --check <file...>          # 只体检不修改
细节：
- A: 删除所有 data-page-node-id 及其它 data-* 属性（秀米/编辑器往返注入，微信会据此整段重置样式）。
- C: <div> -> <p>；</div> -> </p>；把"白字大标题" <p style="...color:#fff...">...<br>...</p>
     拆成多个独立 <p style="...color:#fff;text-align:center;display:block">，一行一个（br 会断白色继承）。
- B: 用 HTMLParser 遍历，td/section/th 自身带 color 时，把其"顶层裸文字"用 <span style="color:同色">包住，
     再从 td/section/th 删除 color（背景/内边距保留）；装饰竖条(仅&nbsp;)不包；
     已自带 color 的内层标签(b/strong/span)内部文字不重复包色，避免覆盖强调色。
"""
import re, sys
from html.parser import HTMLParser

WHITE = ("#fff","#ffffff")

# ---------- A: 剥 data-* ----------
def strip_data(h):
    return re.sub(r'\s*data-[a-zA-Z0-9\-]+="[^"]*"','',h)

# ---------- C: div -> p ----------
def div_to_p(h):
    h=re.sub(r'<div\b','<p',h)
    h=h.replace('</div>','</p>')
    # h1-h4 -> p（微信会重置 h 标签默认样式，统一用 p 承载内联样式）
    for n in (1,2,3,4):
        h=re.sub(rf'<h{n}\b',f'<p',h)
        h=h.replace(f'</h{n}>','</p>')
    return h

# ---------- C: 白字标题拆 br ----------
def split_white_br(h):
    def repl(m):
        openstyle=m.group(1); inner=m.group(2)
        if '<br' not in inner: return m.group(0)
        parts=[p.strip() for p in re.split(r'<br\s*/?>',inner) if p.strip()]
        if len(parts)<2: return m.group(0)
        out=[]
        for idx,p in enumerate(parts):
            mb='margin:0 0 10px;' if idx<len(parts)-1 else 'margin:0 0 14px;'
            out.append(f'<p style="{mb}line-height:1.5;font-weight:bold;color:#ffffff;text-align:center;display:block;">{p}</p>')
        return "".join(out)
    # 匹配含 color:#fff 的 <p ...>...（可含br）...</p>
    pat=re.compile(r'<p\b[^>]*style="([^"]*color:\s*#(?:fff|ffffff)[^"]*)"[^>]*>(.*?)</p>',re.S)
    return pat.sub(repl,h)

# ---------- 合并重复 style ----------
def merge_styles(tagtext):
    styles=re.findall(r'style="([^"]*)"',tagtext)
    if len(styles)<=1: return tagtext
    merged={};order=[]
    for s in styles:
        for decl in s.split(";"):
            decl=decl.strip()
            if not decl or ":" not in decl: continue
            k,v=decl.split(":",1);k=k.strip();v=v.strip()
            if k not in merged: order.append(k)
            merged[k]=v
    ms=";".join(f"{k}:{merged[k]}" for k in order)
    t=re.sub(r'\s*style="[^"]*"','',tagtext)
    return t[:-1]+f' style="{ms}">'

def get_color(style):
    m=re.search(r'(?:^|;)\s*color\s*:\s*(#[0-9a-fA-F]{3,6}|[a-zA-Z]+)',style)
    return m.group(1) if m else None

def del_color(style):
    parts=[p for p in style.split(";") if p.strip() and not re.match(r'\s*color\s*:',p)]
    return ";".join(p.strip() for p in parts if p.strip())

class ColorSinker(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.out=[]; self.track=[]
    def _emit(self,s):
        if self.track and self.track[-1]["color"]:
            self.track[-1]["buf"].append(s)
        else: self.out.append(s)
    def handle_starttag(self,tag,attrs):
        full=merge_styles(self.get_starttag_text())
        m=re.search(r'style="([^"]*)"',full); style=m.group(1) if m else ""
        color=get_color(style)
        if tag in ("td","section","th") and color:
            new_style=del_color(style)
            if new_style: new_open=re.sub(r'style="[^"]*"',f'style="{new_style}"',full)
            else: new_open=re.sub(r'\s*style="[^"]*"','',full)
            self.track.append({"tag":tag,"color":color,"buf":[],"open":new_open,"depth":0})
            return
        if self.track and self.track[-1]["color"]:
            self.track[-1]["buf"].append(full)
            if tag not in ("br","img","hr","input","meta","link","area","base","col","embed","source","track","wbr"):
                self.track[-1]["depth"]+=1
            return
        self.out.append(full)
    def handle_startendtag(self,tag,attrs):
        self._emit(merge_styles(self.get_starttag_text()))
    def handle_endtag(self,tag):
        if self.track and self.track[-1]["color"] and self.track[-1]["tag"]==tag and self.track[-1]["depth"]==0:
            t=self.track.pop()
            inner=self._wrap("".join(t["buf"]),t["color"])
            self.out.append(t["open"]);self.out.append(inner);self.out.append(f"</{tag}>")
            return
        if self.track and self.track[-1]["color"]:
            if tag not in ("br","img","hr","input"): self.track[-1]["depth"]-=1
            self.track[-1]["buf"].append(f"</{tag}>")
            return
        self.out.append(f"</{tag}>")
    def _wrap(self,inner,color):
        tokens=re.split(r'(<[^>]+>)',inner); res=[]; supp=[]
        void={"br","img","hr","input","meta","link","area","base","col","embed","source","track","wbr"}
        for tok in tokens:
            if not tok: continue
            if tok.startswith("</"):
                tn=re.match(r'</\s*([a-zA-Z0-9]+)',tok)
                tn=tn.group(1).lower() if tn else None
                if supp and supp[-1]==tn: supp.pop()
                res.append(tok)
            elif tok.startswith("<"):
                tm=re.match(r'<\s*([a-zA-Z0-9]+)',tok); tn=tm.group(1).lower() if tm else None
                selfclose=tok.rstrip().endswith("/>") or tn in void
                sm=re.search(r'style="([^"]*)"',tok)
                hasc=bool(sm and get_color(sm.group(1)))
                res.append(tok)
                if not selfclose and hasc: supp.append(tn)
            else:
                vis=tok.replace("&nbsp;","").strip()
                if vis and not supp: res.append(f'<span style="color:{color};">{tok}</span>')
                else: res.append(tok)
        return "".join(res)
    def handle_data(self,d): self._emit(d)
    def handle_entityref(self,n): self._emit(f"&{n};")
    def handle_charref(self,n): self._emit(f"&#{n};")

def sink_colors(h):
    p=ColorSinker();p.feed(h);p.close()
    return "".join(p.out)

# ---------- 体检 ----------
def audit(h):
    iss=[]
    did=h.count("data-page-node-id")+len(re.findall(r'\s*data-[a-zA-Z0-9\-]+=',h))
    if did: iss.append(f"A:data-id {did}")
    dv=len(re.findall(r'<div\b',h))
    if dv: iss.append(f"C:div {dv}")
    wbr=len(re.findall(r'color:\s*#(?:fff|ffffff)\b[^>]*>[^<]*<br',h))
    if wbr: iss.append(f"C:白字br {wbr}")
    tdc=len(re.findall(r'<(?:td|section|th)\b[^>]*\bcolor:',h))
    if tdc: iss.append(f"B:td/sec/th色 {tdc}")
    dup=len(re.findall(r'style="[^"]*"\s+style="',h))
    if dup: iss.append(f"重复style {dup}")
    bad=[]
    for tag,pat in [("img",r'<img'),("class",r'class='),("style块",r'<style'),("ul/li",r'<[uo]l|<li'),("h1-4",r'<h[1-4]')]:
        n=len(re.findall(pat,h))
        if n: bad.append(f"{tag}{n}")
    if bad: iss.append("违禁["+"/".join(bad)+"]")
    # 配平
    for t in ("table","tr","td","section","p","span","b","strong","div"):
        d=len(re.findall(rf'<{t}\b',h))-len(re.findall(rf'</{t}>',h))
        if d: iss.append(f"配平!{t}{d:+d}")
    return iss

def process(f, do_fix):
    h=open(f,encoding="utf-8").read()
    before=audit(h)
    if do_fix and before:
        h=strip_data(h); h=div_to_p(h); h=split_white_br(h); h=sink_colors(h)
        open(f,"w",encoding="utf-8").write(h)
    after=audit(h)
    return before,after

if __name__=="__main__":
    args=sys.argv[1:]
    do_fix=True
    if args and args[0]=="--check":
        do_fix=False; args=args[1:]
    total_ok=0; total_bad=0
    for f in args:
        before,after=process(f,do_fix)
        name=f.replace("\\","/").split("/")[-1]
        if not after:
            total_ok+=1; print(f"✅ {name}"+("" if not before else f"  (修复前: {';'.join(before)})"))
        else:
            total_bad+=1
            print(f"❌ {name}")
            if before: print(f"    修前: {';'.join(before)}")
            print(f"    修后: {';'.join(after)}")
    print(f"\n合格 {total_ok} / {total_ok+total_bad}")
