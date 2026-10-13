# -*- coding: utf-8 -*-
"""把「## 二、提词器文案」段里的断句符 // 规范成空格（不影响锚点连续，保留断句视觉）。"""
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
    new_body = re.sub(r"\s*//\s*", " ", body)
    if new_body != body:
        text = text[:m.start(2)] + new_body + text[m.end(2):]
        p.write_text(text, encoding="utf-8")
        changed.append(p.parent.name)

print("规范提词器 // 的篇数：", len(changed))
