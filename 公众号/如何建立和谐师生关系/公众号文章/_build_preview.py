"""生成五篇完整正文派生预览；只复制正文，不修改正文。"""
from pathlib import Path
import hashlib
import html
import importlib.util
import json
import re
import shutil

BASE = Path(__file__).resolve().parent
SOURCES = [
    BASE / "发布包_第1篇_先听委屈/长图文发布包/正文_第1篇_先听委屈.html",
    BASE / "发布包_第2篇_挡枪/长图文发布包/正文_第2篇_挡枪.html",
    BASE / "发布包_第3篇_媒婆/长图文发布包/正文_第3篇_媒婆.html",
    BASE / "发布包_第4篇_拜菩萨/长图文发布包/正文_第4篇_拜菩萨.html",
    BASE / "发布包_第5篇_具体修复/长图文发布包/正文_第5篇_具体修复.html",
]
LABELS = {1: "先听委屈", 2: "挡枪", 3: "媒婆", 4: "拜菩萨", 5: "具体修复"}
tool = BASE.parents[1] / "工具脚本/模板感诊断_template_scan.py"
spec = importlib.util.spec_from_file_location("template_scan", tool)
scan = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scan)
outdir = BASE / "_预览"
outdir.mkdir(exist_ok=True)
articles, buttons, audit = [], [], []
for index, source in enumerate(SOURCES):
    raw = source.read_text(encoding="utf-8")
    body = re.search(r"<body[^>]*>(.*?)</body>", raw, re.S).group(1)
    title = html.unescape(re.search(r"<title>(.*?)</title>", raw).group(1))
    paragraphs = [html.unescape(re.sub(r"<[^>]*>", "", p)) for p in re.findall(r"<p\b[^>]*>(.*?)</p>", body, re.S)]
    count = lambda t: len(re.sub(r"\s", "", t))
    num = index + 1
    duplicate = outdir / f"正文预览_第{num}篇.html"
    duplicate.write_bytes(source.read_bytes())
    assert duplicate.read_bytes() == source.read_bytes()
    cover = source.parent / f"封面_第{num}篇_{LABELS[num]}.jpg"
    shutil.copyfile(cover, outdir / cover.name)
    assert cover.read_bytes() == (outdir / cover.name).read_bytes()
    loading = 'fetchpriority="high"' if index == 0 else 'loading="lazy"'
    coverblock = f'<figure class="cover"><img src="{cover.name}" width="1200" height="511" alt="第{num}篇人物封面：{LABELS[num]}" {loading}><figcaption>封面为AI生成情境，仅供展示；复制正文时不要选取本图。</figcaption></figure>'
    hidden = " hidden" if index else ""
    articles.append(f'<article class="art" id="article{num}" aria-labelledby="preview-title{num}"{hidden}><h2 id="preview-title{num}" class="preview-heading" tabindex="-1">第{num}篇 · {LABELS[num]} · 正式文章</h2>{coverblock}{body}</article>')
    buttons.append(f'<button type="button" id="pick{num}" aria-controls="article{num}" aria-pressed="{str(not index).lower()}" onclick="show({index},true)">第{num}篇 · {LABELS[num]}</button>')
    mainraw = re.sub(r'<!-- 附录开始 -->.*?<!-- 附录结束 -->', '', raw, flags=re.S)
    mainparagraphs = [html.unescape(re.sub(r"<[^>]*>", "", p)) for p in re.findall(r"<p\b[^>]*>(.*?)</p>", mainraw, re.S)]
    visible = scan.visible_text(raw)
    lengths = scan.para_lengths(raw)
    audit.append({
        "篇号": num, "标题": title, "文件": str(source.relative_to(BASE)),
        "全页面可见字符": count("".join(paragraphs)),
        "正文字符_不含眉题标题署名说明及附录": count("".join(mainparagraphs[4:-1])),
        "附录字符": count("".join(paragraphs))-count("".join(mainparagraphs)),
        "统一来源声明": "扶鹰教育-王金海课程" in paragraphs[-1],
        "最长段": max(lengths), "超过180字段数": sum(v > 180 for v in lengths),
        "不是而是句式": len(scan.PAT_BUER.findall(visible)),
        "顿悟节流词": {w: visible.count(w) for w in scan.SAME_WORDS},
        "结构诊断": scan.structure_profile(raw),
        "SHA256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "独立预览与源文件逐字节一致": True,
    })

shell = '''<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>挡枪与媒婆 · 完整排版样板评审</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#f1f4f3;color:#333}
header,main,footer{max-width:26rem;margin:0 auto}header{padding:18px 14px 10px}h1{font-size:1.2rem;line-height:1.6;margin:0 0 8px;color:#294d49}
.note{font-size:.85rem;line-height:1.7;margin:0 0 10px;color:#555}nav{display:flex;gap:8px;flex-wrap:wrap}button,a{font-size:.95rem;line-height:1.5}button{padding:9px 14px;border:1px solid #3f6f6a;border-radius:6px;background:#fff;color:#294d49;cursor:pointer}
button[aria-pressed="true"]{background:#3f6f6a;color:#fff;font-weight:bold;text-decoration:underline;text-underline-offset:4px}button:disabled{color:#666;border-color:#aaa;cursor:default}
button:focus-visible,a:focus-visible,h2:focus-visible{outline:3px solid #294d49;outline-offset:3px}
main{padding:6px 10px 16px}article{background:#fff;border:1px solid #d1dbd7;border-radius:8px;overflow-wrap:anywhere}article[hidden]{display:none}.preview-heading{font-size:.85rem;padding:12px 20px;margin:0;background:#edf3f1;color:#294d49;line-height:1.7}
footer{padding:0 14px 24px}.pager{display:flex;justify-content:space-between;gap:8px}.status{font-size:.85rem;color:#555;line-height:1.8}
.skip{display:block;padding:8px 14px;color:#294d49;text-decoration:underline}
.cover{margin:0}.cover img{display:block;width:100%;height:auto}.cover figcaption{padding:10px 20px;font-size:.75rem;line-height:1.7;color:#666;background:#f7f9f8}
</style></head><body>
<a class="skip" href="#content">跳到文章正文</a>
<header><h1>《如何建立和谐师生关系》· 完整排版样板</h1>
<p class="note">本次为第2、3篇完整正文排版，系列共5篇。已含标题色块、核心句、台词卡、重点提示及结尾自我提醒与认知落点，尚无封面。此页仅供评审，不用于粘贴发布。</p>
<nav aria-label="选择样板">__BUTTONS__</nav></header>
<main id="content" tabindex="-1">__ARTICLES__</main>
<footer><p id="status" class="status" role="status">正在查看第2篇 · 本次2篇样板／系列5篇</p><div class="pager"><button id="prev" type="button" onclick="step(-1)">上一样板</button><button id="next" type="button" onclick="step(1)">下一样板</button></div>
<p class="note">键盘左右键可切换；微信客户端预览与真人出声朗读待人工确认。</p></footer>
<script>
const order=[2,3];let current=0;
function show(index,moveFocus=false){
if(index<0||index>=order.length)return;current=index;
order.forEach((num,i)=>{document.getElementById('article'+num).hidden=i!==index;document.getElementById('pick'+num).setAttribute('aria-pressed',String(i===index));});
document.getElementById('prev').disabled=index===0;document.getElementById('next').disabled=index===order.length-1;
document.getElementById('status').textContent='正在查看第'+order[index]+'篇 · 本次2篇样板／系列5篇';
document.title=(index===0?'挡枪':'媒婆')+' · 完整排版样板评审';
if(moveFocus){document.getElementById('preview-title'+order[index]).focus({preventScroll:true});window.scrollTo(0,0);}
}
function step(delta){show(current+delta,true)}
document.addEventListener('keydown',event=>{if(event.altKey||event.ctrlKey||event.metaKey||event.shiftKey||event.target.matches('input,textarea,select,[contenteditable]'))return;if(event.key==='ArrowLeft'){event.preventDefault();step(-1)}if(event.key==='ArrowRight'){event.preventDefault();step(1)}});
show(0);
</script></body></html>'''
shell = shell.replace('挡枪与媒婆 · 完整排版样板评审', '和谐师生关系 · 五篇完整正文预览').replace('《如何建立和谐师生关系》· 完整排版样板', '《如何建立和谐师生关系》· 五篇完整正文')
shell = shell.replace('本次为第2、3篇完整正文排版，系列共5篇。', '全系列5篇完整正文排版，统一注明来源：扶鹰教育-王金海课程。')
shell = shell.replace('选择样板','选择文章').replace('本次2篇样板／系列5篇','共5篇完整正文').replace('正在查看第2篇','正在查看第1篇').replace('上一样板','上一篇').replace('下一样板','下一篇')
shell = shell.replace('const order=[2,3]', 'const order=[1,2,3,4,5]').replace("(index===0?'挡枪':'媒婆')+' · 完整排版样板评审'", "'第'+order[index]+'篇 · 完整正文预览'")
shell = shell.replace('尚无封面。此页仅供评审，不用于粘贴发布。', '封面及正式发布包已齐。此页为派生预览，正文与封面分别展示。')
shell = re.sub(r' onclick="show\((\d+),true\)"', '', shell)
# 导航按钮模板也移除行内事件，统一注册操作。
buttons = [re.sub(r' onclick="show\(\d+,true\)"', '', b) for b in buttons]
shell = shell.replace(' onclick="step(-1)"','').replace(' onclick="step(1)"','')
shell = shell.replace('show(0);', "order.forEach((num,i)=>document.getElementById('pick'+num).addEventListener('click',()=>show(i,true)));\ndocument.getElementById('prev').addEventListener('click',()=>step(-1));\ndocument.getElementById('next').addEventListener('click',()=>step(1));\nshow(0);")
preview = outdir / "和谐师生关系_全部正文预览_5篇.html"
preview.write_text(shell.replace("__BUTTONS__", "".join(buttons)).replace("__ARTICLES__", "\n".join(articles)), encoding="utf-8")
auditdir = BASE / "_过程文件/全文验收"
auditdir.mkdir(parents=True, exist_ok=True)
(auditdir / "内容与哈希核对.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(audit, ensure_ascii=False, indent=2))
print(preview)
