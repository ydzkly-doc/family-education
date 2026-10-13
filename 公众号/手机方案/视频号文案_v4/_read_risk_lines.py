import re
from pathlib import Path

BASE = Path(__file__).resolve().parent
TARGETS = {
    "08": ["到最后", "只剩一个出口"],
    "17": ["闭眼躺着", "一项任务"],
    "19": ["那张纸", "一份通知"],
    "29": ["它真正的作用", "一段时间"],
}

def section(text, start, end):
    m = re.search(re.escape(start) + r"(.*?)" + re.escape(end), text, re.S)
    return m.group(1).strip() if m else ""

for num, keys in TARGETS.items():
    matches = list(BASE.glob(f"{num}_*/视频号文案_*.md"))
    if not matches:
        continue
    p = matches[0]
    text = p.read_text(encoding="utf-8")
    speech = section(text, "## 一、口播文案", "## 二、提词器文案")
    prompter = section(text, "## 二、提词器文案", "## 三、上屏方案")
    print("\n" + "=" * 20, p.parent.name, "=" * 20)
    for title, body in [("口播", speech), ("提词器", prompter)]:
        print(f"\n[{title}]")
        lines = [x.strip() for x in body.splitlines() if x.strip()]
        for i, line in enumerate(lines):
            if any(k in line for k in keys):
                lo = max(0, i - 1)
                hi = min(len(lines), i + 2)
                for j in range(lo, hi):
                    print(("→ " if j == i else "  ") + lines[j])
