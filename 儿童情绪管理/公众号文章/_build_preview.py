from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "_预览" / "儿童情绪管理_全部正文预览_5篇.html"
ARTICLES = [
    (
        "第1篇",
        "管错的不是脾气",
        ROOT / "发布包_第1篇_管错的不是脾气" / "长图文发布包" / "正文_第1篇_孩子发脾气时父母最容易管错的不是脾气.html",
    ),
    (
        "第2篇",
        "先稳住自己",
        ROOT / "发布包_第2篇_先稳住自己" / "长图文发布包" / "正文_第2篇_孩子一摔门父母最先要稳住的其实是自己.html",
    ),
    (
        "第3篇",
        "允许生气不能打人",
        ROOT / "发布包_第3篇_允许生气不能打人" / "长图文发布包" / "正文_第3篇_允许孩子生气不等于允许他打人.html",
    ),
    (
        "第4篇",
        "学校来电先别讲道理",
        ROOT / "发布包_第4篇_学校来电先别讲道理" / "长图文发布包" / "正文_第4篇_孩子在学校闹情绪第一通电话别急着讲道理.html",
    ),
    (
        "第5篇",
        "赖床不只是情绪",
        ROOT / "发布包_第5篇_赖床不只是情绪" / "长图文发布包" / "正文_第5篇_早上叫十遍还不起可能不只是情绪问题.html",
    ),
]


def body_of(path: Path) -> str:
    raw = path.read_text(encoding="utf-8")
    match = re.search(r"<body[^>]*>(.*)</body>", raw, flags=re.I | re.S)
    if not match:
        raise ValueError(f"未找到 body：{path}")
    body = re.sub(r'\sdata-[\w-]+="[^"]*"', "", match.group(1), flags=re.I)
    return body


buttons = "".join(
    f'<button type="button" class="navbtn" data-index="{i}">{number} · {short}</button>'
    for i, (number, short, _) in enumerate(ARTICLES)
)
pages = "".join(
    f'<article class="art{" show" if i == 0 else ""}" id="art{i}">{body_of(path)}</article>'
    for i, (_, _, path) in enumerate(ARTICLES)
)

html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>儿童情绪管理｜全部正文预览（5篇）</title>
<style>
body{{margin:0;background:#ebe7df;color:#303633;font-family:"Microsoft YaHei",sans-serif}}
header{{position:sticky;top:0;z-index:10;background:#254f4b;color:#fff;padding:12px}}
.head{{max-width:760px;margin:0 auto}}
.head p{{margin:0 0 9px;font-size:14px}}
nav{{display:flex;gap:8px;overflow-x:auto;padding-bottom:2px}}
.navbtn{{min-height:34px;border:1px solid #82a6a1;border-radius:18px;background:#315e59;color:#fff;padding:6px 12px;white-space:nowrap;cursor:pointer}}
.navbtn.active{{background:#c99a5b;border-color:#c99a5b;color:#2d251a}}
.navbtn:focus-visible,.pager button:focus-visible{{outline:3px solid #fff;outline-offset:2px}}
main{{max-width:720px;margin:18px auto;padding:0 12px 34px}}
.art{{display:none}}
.art.show{{display:block}}
.pager{{display:flex;justify-content:space-between;gap:12px;margin-top:16px}}
.pager button{{min-height:40px;border:1px solid #9ba9a6;border-radius:8px;background:#fff;color:#315e59;padding:8px 16px;cursor:pointer}}
#status{{text-align:center;color:#65716e;font-size:13px;margin:12px 0}}
@media(max-width:520px){{main{{margin-top:10px;padding-inline:6px}}.head p{{font-size:13px}}}}
</style></head><body>
<header><section class="head"><p>《儿童情绪管理》｜全部正文预览（5篇）</p><nav aria-label="文章选择">{buttons}</nav></section></header>
<main>{pages}<p id="status" aria-live="polite">第 1 篇 / 共 5 篇 · 管错的不是脾气</p><section class="pager"><button type="button" id="prev">◀ 上一篇</button><button type="button" id="next">下一篇 ▶</button></section></main>
<script>
const pages=[...document.querySelectorAll('.art')];
const buttons=[...document.querySelectorAll('.navbtn')];
const labels={list(repr(short) for _, short, _ in ARTICLES)};
let current=0;
function show(index){{current=(index+pages.length)%pages.length;pages.forEach((page,i)=>page.classList.toggle('show',i===current));buttons.forEach((button,i)=>button.classList.toggle('active',i===current));document.getElementById('status').textContent=`第 ${{current+1}} 篇 / 共 ${{pages.length}} 篇 · ${{labels[current]}}`;window.scrollTo({{top:0,behavior:'smooth'}})}}
buttons.forEach((button,i)=>button.addEventListener('click',()=>show(i)));
document.getElementById('prev').addEventListener('click',()=>show(current-1));
document.getElementById('next').addEventListener('click',()=>show(current+1));
document.addEventListener('keydown',event=>{{if(event.key==='ArrowLeft')show(current-1);if(event.key==='ArrowRight')show(current+1)}});
show(0);
</script></body></html>"""

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(html, encoding="utf-8")
print(OUTPUT)
