# -*- coding: utf-8 -*-
import os, re, glob
from docx import Document
from docx.shared import Pt, RGBColor
from docx.oxml.ns import qn

BASE = r"D:\个人资料\家庭教育\为什么学生不喜欢上学\公众号文章"
HTML_DIR = os.path.join(BASE, "排版HTML")
OUT = os.path.join(BASE, "Word版本")
os.makedirs(OUT, exist_ok=True)
CN_FONT = "微软雅黑"

def font(run, size=None, bold=None, color=None):
    run.font.name = CN_FONT
    run._element.rPr.rFonts.set(qn('w:eastAsia'), CN_FONT)
    if size: run.font.size = Pt(size)
    if bold is not None: run.font.bold = bold
    if color: run.font.color.rgb = RGBColor(*color)

def rich(p, text, size=11, base=(44,44,42)):
    for part in re.split(r'(\*\*.+?\*\*)', text):
        if not part: continue
        if part.startswith('**') and part.endswith('**'):
            r=p.add_run(part[2:-2]); font(r,size,True,(15,110,86))
        else:
            r=p.add_run(part); font(r,size,color=base)

def strip_tags(s):
    s = re.sub(r'<br\s*/?>', '\n', s)
    s = re.sub(r'<[^>]+>', '', s)
    s = s.replace('&nbsp;',' ').replace('&amp;','&').replace('&lt;','<').replace('&gt;','>').replace('📌','【').replace('👇','')
    return s.strip()

def convert(html_path, out_path):
    with open(html_path, encoding='utf-8') as f:
        html = f.read()
    doc = Document()
    nm = doc.styles['Normal']; nm.font.name=CN_FONT; nm.font.size=Pt(11)
    nm.element.rPr.rFonts.set(qn('w:eastAsia'), CN_FONT)

    m = re.search(r'<div class="a">(.*?)<div class="src">', html, re.S)
    body = m.group(1) if m else html
    # split into blocks by h1/h2/p/div.slot ; handle tables specially
    token = re.split(r'(<h1[^>]*>.*?</h1>|<h2[^>]*>.*?</h2>|<p[^>]*>.*?</p>|<div class="slot".*?</div>)', body, flags=re.S)
    for t in token:
        if not t or not t.strip(): continue
        hm = re.match(r'<h1[^>]*>(.*?)</h1>', t, re.S)
        h2m = re.match(r'<h2[^>]*>(.*?)</h2>', t, re.S)
        pm = re.match(r'<p[^>]*>(.*?)</p>', t, re.S)
        slotm = re.match(r'<div class="slot".*?>(.*?)</div>', t, re.S)
        if hm:
            p=doc.add_paragraph(); r=p.add_run(strip_tags(hm.group(1))); font(r,17,True,(26,26,24))
        elif h2m:
            p=doc.add_paragraph(); p.paragraph_format.space_before=Pt(12)
            r=p.add_run(strip_tags(h2m.group(1))); font(r,13.5,True,(15,110,86))
        elif slotm:
            p=doc.add_paragraph(); p.paragraph_format.left_indent=Pt(10)
            r=p.add_run('【配图位】' + strip_tags(slotm.group(1))); font(r,10,True,(180,115,15))
        elif pm:
            txt = strip_tags(pm.group(1))
            if not txt: continue
            p=doc.add_paragraph(); p.paragraph_format.line_spacing=1.5; p.paragraph_format.space_after=Pt(8)
            rich(p, txt)
        elif '<table' in t:
            # card: add a note line then dump cell texts
            p=doc.add_paragraph(); r=p.add_run('— 此处为文中图文卡片，详见 HTML 版 —'); font(r,10,True,(120,120,150))
    # source declaration
    src = re.search(r'<div class="src">(.*?)</div>', html, re.S)
    if src:
        p=doc.add_paragraph(); p.paragraph_format.space_before=Pt(14)
        r=p.add_run(strip_tags(src.group(1))); font(r,9.5,color=(150,150,144)); r.font.italic=True
    doc.save(out_path)

for h in sorted(glob.glob(os.path.join(HTML_DIR, "*.html"))):
    name = os.path.splitext(os.path.basename(h))[0]
    convert(h, os.path.join(OUT, name + ".docx"))
    print("OK ->", name + ".docx")
print("DONE")
