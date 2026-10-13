# -*- coding: utf-8 -*-
"""
仅清理「## 二、提词器文案」段里包裹重点词的 【】（保留其中文字）。
- 只动提词器段，不碰口播、上屏方案及其它段落；
- 提词器里的【】原本只是拍摄强调，去掉后锚点整句能逐字连续出现。
"""
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent

SEG_RE = re.compile(r"(## 二、提词器文案)(.*?)(## 三、上屏方案)", re.S)

changed = []
for p in sorted(BASE.glob("[0-9][0-9]_*/视频号文案_*.md")):
    text = p.read_text(encoding="utf-8")
    m = SEG_RE.search(text)
    if not m:
        continue
    body = m.group(2)
    new_body = body.replace("【", "").replace("】", "")
    if new_body != body:
        text = text[:m.start(2)] + new_body + text[m.end(2):]
        p.write_text(text, encoding="utf-8")
        changed.append(p.parent.name)

print("清理提词器【】的篇数：", len(changed))
for c in changed:
    print(" -", c)
