from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent


def article_number(path: Path) -> int:
    match = re.search(r"第(\d+)篇", path.name)
    if not match:
        raise ValueError(f"无法识别篇号：{path}")
    return int(match.group(1))


def main() -> None:
    paths = sorted(
        ROOT.glob("发布包_第*篇_*/长图文发布包/正文_第*.html"),
        key=article_number,
    )
    if not paths:
        raise SystemExit("未找到正式发布包正文")

    articles = []
    buttons = []
    for index, path in enumerate(paths):
        source = path.read_text(encoding="utf-8")
        body_match = re.search(r"<body[^>]*>(.*?)</body>", source, re.S | re.I)
        if not body_match:
            raise ValueError(f"正文缺少 body：{path}")
        state = " show" if index == 0 else ""
        articles.append(f'<section class="art{state}" id="art{index}">{body_match.group(1)}</section>')
        buttons.append(
            f'<button type="button" onclick="show({index})" aria-label="查看第{article_number(path)}篇">'
            f'第{article_number(path)}篇</button>'
        )

    css = """*{box-sizing:border-box}body{margin:0;background:#e8efed;color:#303b39;font-family:'Microsoft YaHei','PingFang SC',sans-serif}header{padding:18px 14px;text-align:center;background:#fff;border-bottom:1px solid #cfddda}h1{font-size:20px;margin:0 0 8px;color:#315955}header p{font-size:13px;margin:5px 0;line-height:1.7;color:#697673}nav{margin-top:10px}button{border:1px solid #3f6f6a;border-radius:22px;background:#fff;color:#315955;padding:8px 20px;margin:4px;cursor:pointer}button[aria-pressed='true']{background:#3f6f6a;color:#fff}main{max-width:680px;margin:18px auto}.art{display:none}.art.show{display:block}footer{text-align:center;padding:10px 8px 20px;position:sticky;bottom:0;background:#fff;border-top:1px solid #cfddda}footer p{margin:0 0 6px;font-size:13px;color:#697673}button:disabled{opacity:.4;cursor:default}@media(max-width:480px){main{margin:0 auto}header{padding:13px 10px}}"""
    script = f"""let current=0;const total={len(paths)};function show(n){{current=Math.max(0,Math.min(total-1,n));document.querySelectorAll('.art').forEach((el,i)=>el.classList.toggle('show',i===current));document.querySelectorAll('nav button').forEach((el,i)=>el.setAttribute('aria-pressed',String(i===current)));document.getElementById('count').textContent='当前第 '+(current+1)+' 篇 / 共 '+total+' 篇';document.getElementById('prev').disabled=current===0;document.getElementById('next').disabled=current===total-1;window.scrollTo(0,0)}}document.addEventListener('keydown',event=>{{if(event.key==='ArrowLeft')show(current-1);if(event.key==='ArrowRight')show(current+1)}});show(0);"""

    page = (
        "<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        "<title>孩子与手机 · 10篇正文预览</title><style>"
        + css
        + "</style></head><body><header><h1>孩子与手机：从冲突管控到自主使用</h1>"
        "<p>全系列10篇正式正文预览 · 长图文封面与卡片发布包已完成</p>"
        "<p>方向键可切换；正式发布前仍需公众号后台及 Android / iOS 预览</p><nav>"
        + "".join(buttons)
        + "</nav></header><main>"
        + "".join(articles)
        + "</main><footer><p id=\"count\"></p>"
        "<button id=\"prev\" onclick=\"show(current-1)\">← 上一篇</button>"
        "<button id=\"next\" onclick=\"show(current+1)\">下一篇 →</button>"
        "</footer><script>"
        + script
        + "</script></body></html>"
    )

    output_dir = ROOT / "_预览"
    output_dir.mkdir(exist_ok=True)
    target = output_dir / "孩子与手机_全部正文预览_10篇.html"
    target.write_text(page, encoding="utf-8")
    print(target)


if __name__ == "__main__":
    main()
