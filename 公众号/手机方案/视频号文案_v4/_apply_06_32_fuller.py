# -*- coding: utf-8 -*-
from pathlib import Path
import re

BASE = Path(r"D:/个人资料/家庭教育/公众号/手机方案/视频号文案_v4")
WORK = BASE / "_06-32完整观点双稿扩写工作稿_20261013.md"
work = WORK.read_text(encoding="utf-8")

for n in range(6, 33):
    pattern = rf"^# {n:02d} .*?(?=^# {n+1:02d} |\Z)" if n < 32 else rf"^# {n:02d} .*?\Z"
    m = re.search(pattern, work, re.S | re.M)
    if not m:
        raise SystemExit(f"工作稿缺少 {n:02d}")
    sec = m.group(0)
    speech = re.search(r"## 新口播文案\s*(.*?)\n## 新提词器文案", sec, re.S).group(1).strip()
    prompter = re.search(r"## 新提词器文案\s*(.*?)\n## 保留锚点检查", sec, re.S).group(1).strip()

    md_paths = list(BASE.glob(f"{n:02d}_*/视频号文案_*.md"))
    if len(md_paths) != 1:
        raise SystemExit(f"目标文件异常 {n:02d}: {md_paths}")
    p = md_paths[0]
    s = p.read_text(encoding="utf-8")

    def replace_between(text, start_title, end_title, new_body):
        pattern = re.escape(start_title) + r".*?" + re.escape(end_title)
        repl = start_title + "\n\n" + new_body.strip() + "\n\n---\n\n" + end_title
        text2, count = re.subn(pattern, repl, text, count=1, flags=re.S)
        if count != 1:
            raise SystemExit(f"替换失败 {p}: {start_title}")
        return text2

    s = replace_between(s, "## 一、口播文案", "## 二、提词器文案", speech)
    s = replace_between(s, "## 二、提词器文案", "## 三、上屏方案", prompter)

    chars = len(re.findall(r"[\u4e00-\u9fffA-Za-z0-9]", speech))
    secs = chars / 4.3
    mm = int(secs // 60)
    ss = int(round(secs - mm * 60))
    low = max(60, int(secs) + 8)
    high = int(secs) + 15
    new_head = f"时长 ≈{mm}:{ss:02d}（完整观点条复核 2026-10-13：正文 {chars} 字 ÷4.3 ≈{secs:.0f} 秒，加停顿真片预计 {low}~{high} 秒；目标 90~120 秒，硬上限 3:30）"
    s2 = re.sub(r"时长 ≈[^｜｜]+(｜ 形态)", new_head + r" ｜ 形态", s, count=1)
    if s2 != s:
        s = s2

    p.write_text(s, encoding="utf-8")
    print(f"{n:02d} applied {chars} chars -> {p.parent.name}")
