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

    stage_map = {
        1: "A 看清问题", 2: "A 看清问题",
        3: "B 看懂吸引力", 4: "B 看懂吸引力", 5: "B 看懂吸引力",
        6: "B 看懂吸引力", 7: "B 看懂吸引力",
        8: "C 重建家庭系统", 9: "C 重建家庭系统",
        10: "C 重建家庭系统", 11: "C 重建家庭系统",
        12: "D 行动与退出", 13: "D 行动与退出", 14: "D 行动与退出",
    }
    articles = []
    buttons = []
    previous_stage = None
    for index, path in enumerate(paths):
        number = article_number(path)
        stage = stage_map[number]
        source = path.read_text(encoding="utf-8")
        body_match = re.search(r"<body[^>]*>(.*?)</body>", source, re.S | re.I)
        if not body_match:
            raise ValueError(f"正文缺少 body：{path}")
        state = " show" if index == 0 else ""
        articles.append(f'<section class="art{state}" id="art{index}">{body_match.group(1)}</section>')
        if stage != previous_stage:
            buttons.append(f'<span class="stage-label">{stage}</span>')
            previous_stage = stage
        buttons.append(
            f'<button type="button" data-stage="{stage}" onclick="show({index})" aria-label="查看第{number}篇">'
            f'第{number}篇</button>'
        )

    css = """*{box-sizing:border-box}body{margin:0;background:#e8efed;color:#303b39;font-family:'Microsoft YaHei','PingFang SC',sans-serif}header{padding:18px 14px;text-align:center;background:#fff;border-bottom:1px solid #cfddda}h1{font-size:20px;margin:0 0 8px;color:#315955}header p{font-size:13px;margin:5px 0;line-height:1.7;color:#697673}nav{margin-top:10px}.stage-label{display:inline-block;border-radius:999px;background:#315955;color:#f3d5ad;padding:8px 12px;margin:4px 2px;font-size:12px;font-weight:700}button{border:1px solid #3f6f6a;border-radius:22px;background:#fff;color:#315955;padding:8px 16px;margin:4px;cursor:pointer}button[aria-pressed='true']{background:#c99a5b;border-color:#c99a5b;color:#fff}main{max-width:680px;margin:18px auto}.art{display:none}.art.show{display:block}footer{text-align:center;padding:10px 8px 20px;position:sticky;bottom:0;background:#fff;border-top:1px solid #cfddda}footer p{margin:0 0 6px;font-size:13px;color:#697673}button:disabled{opacity:.4;cursor:default}@media(max-width:480px){main{margin:0 auto}header{padding:13px 10px}.stage-label{display:block;width:max-content;margin:8px auto 3px}}"""
    script = f"""let current=0;const total={len(paths)};function show(n){{current=Math.max(0,Math.min(total-1,n));document.querySelectorAll('.art').forEach((el,i)=>el.classList.toggle('show',i===current));const buttons=[...document.querySelectorAll('nav button')];buttons.forEach((el,i)=>el.setAttribute('aria-pressed',String(i===current)));const stage=buttons[current].dataset.stage;document.getElementById('count').textContent=stage+' · 当前第 '+(current+1)+' 篇 / 共 '+total+' 篇';document.getElementById('prev').disabled=current===0;document.getElementById('next').disabled=current===total-1;window.scrollTo(0,0)}}document.addEventListener('keydown',event=>{{if(event.key==='ArrowLeft')show(current-1);if(event.key==='ArrowRight')show(current+1)}});show(0);"""

    page = (
        "<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        "<title>孩子与手机 · 14篇正文预览</title><style>"
        + css
        + "</style></head><body><header><h1>孩子与手机：从冲突管控到自主使用</h1>"
        "<p>全系列14篇正式正文预览 · 长图文发布包与封面已完成</p>"
        "<p>14篇长图文与后台派生卡片发布包均已完成；第14篇含完整家庭工具包</p>"
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
    target = output_dir / "孩子与手机_全部正文预览_14篇.html"
    target.write_text(page, encoding="utf-8")
    print(target)


if __name__ == "__main__":
    main()
