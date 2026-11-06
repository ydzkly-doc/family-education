# -*- coding: utf-8 -*-
from pathlib import Path
import json
import re

LOG = Path("C:/Users/ZhuanZ/.workbuddy/projects/d-个人资料-家庭教育/e5608de3-c823-4673-afbc-f577ce191d6d.jsonl")
ROOT = Path("D:/个人资料/家庭教育/公众号/手机方案/视频号文案_v4")
found = {}
for line in LOG.read_text(encoding="utf-8").splitlines():
    row = json.loads(line)
    if row.get("type") != "function_call_result" or row.get("name") != "Read":
        continue
    text = row.get("output", {}).get("text", "")
    match = re.search(r"^\s*1→# 视频号文案 · (\d\d)", text, re.M)
    if not match:
        continue
    number = int(match.group(1))
    if not 13 <= number <= 32:
        continue
    if number not in {20, 21, 23} and "2026-10-28" not in text:
        continue
    if number in found:
        continue
    lines = []
    for source in text.splitlines():
        parsed = re.match(r"\s*\d+→(.*)$", source)
        if parsed:
            lines.append(parsed.group(1))
    content = "\n".join(lines)
    paths = list(ROOT.glob(f"{number:02d}_*/视频号文案_*.md"))
    if len(paths) == 1 and len(content) > 4000:
        found[number] = (paths[0], content)
for number, (path, content) in found.items():
    path.write_text(content, encoding="utf-8")
    print(number, len(content), path.name)
print("RESTORED", len(found))
if len(found) != 20:
    raise SystemExit("快照不足20条，未完整恢复")
