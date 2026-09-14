from html import unescape
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent


def article_number(path: Path) -> int:
    match = re.search(r"第(\d+)篇", path.name)
    if not match:
        raise ValueError(f"无法识别篇号：{path}")
    return int(match.group(1))


def collect_articles() -> list[Path]:
    by_number: dict[int, Path] = {}
    for path in ROOT.glob("发布包_第*篇_*/正文_*.html"):
        by_number[article_number(path)] = path
    return [by_number[number] for number in sorted(by_number)]


def extract_title(source: str) -> str:
    match = re.search(r"<title>(.*?)</title>", source, re.S)
    return unescape(match.group(1)).strip() if match else "未命名文章"


def main() -> None:
    paths = collect_articles()
    if not paths:
        raise SystemExit("未找到样板、正文稿或正式正文")

    articles = []
    buttons = []
    for index, path in enumerate(paths):
        source = path.read_text(encoding="utf-8")
        body = re.search(r"<body[^>]*>(.*?)</body>", source, re.S)
        if not body:
            raise ValueError(f"正文缺少 body：{path}")
        title = extract_title(source)
        articles.append(
            f'<section class="art{" show" if index == 0 else ""}" id="art{index}">'
            f'<p class="source">正式第{article_number(path)}篇｜{title}</p>{body.group(1)}</section>'
        )
        buttons.append(
            f'<button type="button" onclick="show({index})" aria-label="查看第{article_number(path)}篇">'
            f'第{article_number(path)}篇</button>'
        )

    css = """*{box-sizing:border-box}body{margin:0;background:#E8E3DC;color:#34383B;font-family:\"Microsoft YaHei\",sans-serif}header{padding:20px 16px;text-align:center;background:#F8F5F0;border-bottom:1px solid #D8D0C6}h1{font-size:21px;margin:0 0 8px;color:#46535E}header p,.source{font-size:13px;margin:6px 0;line-height:1.7}.source{padding:8px 12px;background:#FFF7ED;color:#7A532D}button{border:1px solid #46535E;border-radius:24px;background:#fff;color:#46535E;padding:9px 22px;margin:5px;cursor:pointer}button[aria-pressed=\"true\"]{background:#46535E;color:white}main{max-width:640px;margin:20px auto}.art{display:none}.art.show{display:block}footer{text-align:center;padding:12px 8px 25px;position:sticky;bottom:0;background:#F8F5F0;border-top:1px solid #D8D0C6}button:disabled{opacity:.4;cursor:default}@media(max-width:480px){main{margin:0 auto}header{padding:14px 12px}}"""
    script = f"""let current=0;const total={len(paths)};function show(n){{current=Math.max(0,Math.min(total-1,n));document.querySelectorAll('.art').forEach((e,i)=>e.classList.toggle('show',i===current));document.querySelectorAll('nav button').forEach((e,i)=>e.setAttribute('aria-pressed',String(i===current)));document.getElementById('count').textContent='第 '+(current+1)+' 篇 / 共 '+total+' 篇';document.getElementById('prev').disabled=current===0;document.getElementById('next').disabled=current===total-1;window.scrollTo(0,0)}}document.addEventListener('keydown',e=>{{if(e.key==='ArrowRight')show(current+1);if(e.key==='ArrowLeft')show(current-1)}});show(0);"""
    page = (
        '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>我们到底在吵什么 · 全部正文预览</title><style>'
        + css
        + '</style></head><body><header><h1>我们到底在吵什么</h1>'
        + f'<p>正式正文 · 当前共{len(paths)}篇 · 以微信后台粘贴后的手机预览为最终依据</p><nav>'
        + "".join(buttons)
        + '</nav></header><main>'
        + "".join(articles)
        + '</main><footer><p id="count"></p><button id="prev" onclick="show(current-1)">← 上一篇</button>'
        + '<button id="next" onclick="show(current+1)">下一篇 →</button></footer><script>'
        + script
        + '</script></body></html>'
    )
    preview_dir = ROOT / "_预览"
    preview_dir.mkdir(exist_ok=True)
    target = preview_dir / f"我们到底在吵什么_全部正文预览_{len(paths)}篇.html"
    target.write_text(page, encoding="utf-8")
    print(target)


if __name__ == "__main__":
    main()
