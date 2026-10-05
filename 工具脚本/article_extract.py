# -*- coding: utf-8 -*-
"""把公众号正文 HTML 提取成纯文本（供视频号写稿时对账／引用原文）。

用法：
    python article_extract.py "<正文.html>"                # 打印到 stdout
    python article_extract.py "<正文.html>" --out x.txt    # 写到文件（推荐，避免控制台编码问题）

说明：剥掉全部标签，段落按行输出，去空行；实体做基础还原。
"""
import argparse
import re
import sys

TAG_RE = re.compile(
    r"<script[\s\S]*?</script>|<style[\s\S]*?</style>"
    r"|<br\s*/?>|</p>|</section>|</div>|</li>|</h[1-6]>"
    r"|<[^>]+>",
    re.I,
)
ENT = {
    "&nbsp;": " ", "&amp;": "&", "&lt;": "<", "&gt;": ">",
    "&ldquo;": "\u201c", "&rdquo;": "\u201d",
    "&lsquo;": "\u2018", "&rsquo;": "\u2019",
    "&mdash;": "\u2014", "&hellip;": "\u2026", "&quot;": "\u0022",
}


def clean(html: str) -> str:
    txt = TAG_RE.sub("\n", html)
    for k, v in ENT.items():
        txt = txt.replace(k, v)
    txt = re.sub(r"[ \t\u00a0]+", " ", txt)
    lines = [l.strip() for l in txt.split("\n")]
    lines = [l for l in lines if l]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("html", help="正文 html 路径")
    ap.add_argument("--out", help="输出到文件（utf-8）")
    a = ap.parse_args()
    with open(a.html, "r", encoding="utf-8", errors="ignore") as f:
        raw = f.read()
    txt = clean(raw)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(txt)
        print(f"已写出 {a.out}（{len(txt)} 字符）")
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        print(txt)


if __name__ == "__main__":
    main()
