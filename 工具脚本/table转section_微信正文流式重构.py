# -*- coding: utf-8 -*-
"""
table转section_微信正文流式重构.py
把微信公众号正文 HTML 的 <table> 布局转为 <section> 流式布局。
根因：微信安卓 X5 内核会把 <table> 宽度固化、窄屏整列右裁（iOS 正常）；
      <section> 块 width:100% + box-sizing:border-box 在安卓/iOS 都自适应。

做法（标签级正则映射，开闭严格一一对应，不依赖 DOM 栈，兼容 section/table 混排）：
  <table ...>  -> <section ...>   </table> -> </section>
  <tr ...>     -> <section ...>   </tr>    -> </section>
  <td ...>/<th ...> -> <section ...>  </td></th> -> </section>
  <tbody/thead>  -> 去掉标签（内容保留）
样式清洗：剥固定 px 宽(width/max-width/min-width)、表格专属属性(border-collapse/vertical-align)、
         data-* 属性、cellpadding/cellspacing/border/role/colspan/rowspan/width 属性；
         每个块注入 box-sizing:border-box;width:100%;display:block；
竖条小标题(width:4-8px 色条单元格) -> 整格删除，由后处理给相邻标题补 border-left；
多列网格单元格(带 width="NN%") -> 满宽堆叠、加 margin-bottom。
用法：
  python table转section_微信正文流式重构.py <文件.html> [...]
  --check 仅统计 <table> 数，不写文件
"""
import sys, re, os

DROP_TAG_ATTRS = {"cellpadding","cellspacing","border","role","width","height",
                  "colspan","rowspan","valign","align","data-w"}
DROP_STYLE_KEYS = {"border-collapse","border-spacing","table-layout","vertical-align"}

def clean_style(style, is_bar=False, is_grid_cell=False):
    if not style:
        style = ""
    decls = [d.strip() for d in style.split(";") if d.strip()]
    out=[]; seen=set()
    for d in decls:
        if ":" not in d: continue
        k=d.split(":",1)[0].strip().lower()
        v=d.split(":",1)[1].strip()
        if k in DROP_STYLE_KEYS: continue
        if k in ("max-width","min-width"): continue
        if k=="width":
            # 保留 100%；剥固定 px（竖条 width:6px 整格会被删，这里也剥）
            if v.replace(" ","").endswith("px"):
                continue
        if k in seen: continue
        seen.add(k); out.append(f"{k}:{v}")
    s=";".join(out)
    if is_bar:
        return s  # 竖条格整体删除，样式不重要
    # 注入盒模型
    if "box-sizing" not in seen:
        s="box-sizing:border-box;"+s
    if "width" not in seen:
        s=s+";width:100%"
    if "display" not in seen:
        s=s+";display:block"
    if is_grid_cell and "margin-bottom" not in seen:
        s=s+";margin-bottom:8px"
    return s

def conv_open_tag(tagname, attrs_raw):
    """把一个 <table/tr/td> 开标签转成 <section>，返回 (html, is_bar)"""
    # 解析属性
    attrs=dict(re.findall(r'([a-zA-Z_:][-a-zA-Z0-9_:]*)="([^"]*)"', attrs_raw))
    style=attrs.get("style","")
    width_attr=attrs.get("width","")
    # 竖条色条单元格：style 含 width:4-10px 且 font-size:0 / 仅 &nbsp;
    m=re.search(r"width:\s*(\d+)px", style)
    is_bar=False
    if tagname in ("td","th") and m and int(m.group(1))<=10 and ("font-size:0" in style.replace(" ","") or "line-height:0" in style.replace(" ","")):
        is_bar=True
    # 多列网格单元格：td/th 带 width="NN%"
    is_grid = tagname in ("td","th") and "%" in width_attr
    if is_bar:
        return ("@@BAR_OPEN@@", True)
    style=clean_style(style, is_grid_cell=is_grid)
    # 多列网格：不对称圆角统一
    style=style.replace("border-radius:8px 0 0 8px","border-radius:8px").replace("border-radius:0 8px 8px 0","border-radius:8px")
    attr=f' style="{style}"' if style else ""
    return (f"<section{attr}>", False)

def convert(html):
    # 1) 先剥 tbody/thead 开闭标签（保留内容）
    html=re.sub(r"</?tbody[^>]*>","",html)
    html=re.sub(r"</?thead[^>]*>","",html)

    # 2) 处理竖条单元格：竖条特征是 style 含 width:4-10px 且 font-size:0/line-height:0，
    #    内容只有 &nbsp;，与闭合 </td> 在同一行（不跨行通配，避免灾难性回溯）。
    html=re.sub(
        r'<td\b[^>]*style="[^"]*(?:width:\s*(?:[4-9]|10)px[^"]*font-size:0|font-size:0[^"]*width:\s*(?:[4-9]|10)px)[^"]*"[^>]*>\s*&nbsp;\s*</td>',
        "", html)

    # 3) table/tr/td/th 开标签 -> section
    def open_repl(m):
        tag=m.group(1); raw=m.group(2)
        html2,is_bar=conv_open_tag(tag, raw)
        return html2
    html=re.sub(r"<(table|tr|td|th)\b([^>]*)>", open_repl, html)

    # 3.5) <div> -> <section>（微信对 div 渲染不稳），开闭都转
    html=re.sub(r"<div\b([^>]*)>", lambda m: "<section"+m.group(1)+">", html)
    html=html.replace("</div>","</section>")

    # 4) 闭合标签
    html=html.replace("</table>","</section>").replace("</tr>","</section>")
    html=html.replace("</td>","</section>").replace("</th>","</section>")

    # 4.5) 全局剥除所有标签上的 data-* 属性（编辑器/预览注入）
    html=re.sub(r'\s+data-[a-zA-Z0-9\-]+="[^"]*"', '', html)
    html=re.sub(r"\s+data-[a-zA-Z0-9\-]+='[^']*'", '', html)

    # 5) 残留 @@BAR_OPEN@@ 兜底（不应有）
    html=html.replace("@@BAR_OPEN@@","")

    # 5.5) 全局剥除“容器级固定宽度”——不管在 table 转的还是原生 section 上：
    #   max-width:NNNpx（NNN>=200，如 677/680/700 容器）-> 删除，改 width:100%
    #   width:NNNpx（NNN>=200 的块级容器）-> 删除（保留 22px 序号圆点等小装饰）
    def strip_container_width(m):
        style=m.group(1)
        # 剥 max-width: 大px
        style=re.sub(r"max-width:\s*\d{3,}px;?", "", style)
        # 剥 width: 大px（>=200）
        def w_rep(mm):
            num=int(mm.group(1))
            return "" if num>=200 else mm.group(0)
        style=re.sub(r"width:\s*(\d{3,})px;?", w_rep, style)
        # 若原本靠 max-width+margin auto 居中，去掉 max-width 后 margin:0 auto 无意义但无害；保留
        style=style.replace(";;",";").strip(";")
        return f'style="{style}"'
    html=re.sub(r'style="([^"]*)"', strip_container_width, html)

    # 6) 后处理
    html=post_fix(html)
    return html

def post_fix(s):
    # 竖条标题补 border-left：padding-left:12px + 大字粗体 的 section
    def add_border(m):
        style=m.group(1)
        if "border-left" in style: return m.group(0)
        if re.search(r"font-size:\s*(18|19|20|21)px", style) and "font-weight:bold" in style:
            style=style.replace("padding-left:12px","").strip(";")
            return f'<section style="border-left:5px solid #c0764f;padding-left:14px;{style}">'
        return m.group(0)
    s=re.sub(r'<section style="([^"]*padding-left:12px[^"]*)">', add_border, s)
    # 空色条残留
    s=re.sub(r'<section style="[^"]*font-size:0[^"]*">\s*&nbsp;\s*</section>', '', s)
    # 双分号/空style
    s=s.replace(";;",";")
    s=re.sub(r'style="\s*"','',s)
    # 折叠空行
    s=re.sub(r"\n[ \t]*\n[ \t]*\n+","\n\n",s)
    return s

def count_table(path):
    return len(re.findall(r"<table[ >]", open(path,encoding="utf-8").read(), re.I))

if __name__=="__main__":
    args=sys.argv[1:]
    do_check="--check" in args
    files=[a for a in args if not a.startswith("--")]
    if do_check:
        for f in files:
            print(f"{count_table(f):3d} 个<table>  {f}")
        sys.exit(0)
    for f in files:
        if not os.path.isfile(f):
            print("跳过(不存在):",f); continue
        h=open(f,encoding="utf-8").read()
        had="<table" in h.lower()
        out=convert(h)
        open(f,"w",encoding="utf-8").write(out)
        nt=len(re.findall(r"<table[ >]",out,re.I))
        so=len(re.findall(r"<section[ >]",out)); sc=out.count("</section>")
        po=len(re.findall(r"<p[ >]",out)); pc=out.count("</p>")
        flag="✅" if (nt==0 and so==sc and po==pc) else "⚠️"
        print(f"{flag} {os.path.basename(f)}  table{nt} sec{so}/{sc} p{po}/{pc} (原含table:{had})")
