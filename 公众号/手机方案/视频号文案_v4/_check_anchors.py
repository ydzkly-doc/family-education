import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
SKILL_SCRIPTS = Path(r"D:\个人资料\家庭教育\_技能\ffmpeg-vertical-video-pipeline\scripts")
sys.path.insert(0, str(SKILL_SCRIPTS))
from md_spec import parse_md  # noqa: E402

DROP = r"[\s，。？！、；：「」『』“”\"'（）()≠=·…—\-—:：]+"

def flat(text: str) -> str:
    return re.sub(DROP, "", text or "")

def section(text: str, start: str, end: str) -> str:
    m = re.search(re.escape(start) + r"(.*?)" + re.escape(end), text, re.S)
    return m.group(1) if m else ""

def count_cn(text: str) -> int:
    return len(re.findall(r"[\u4e00-\u9fffA-Za-z0-9]", text))

for p in sorted(BASE.glob("[0-9][0-9]_*/视频号文案_*.md")):
    text = p.read_text(encoding="utf-8")
    speech = section(text, "## 一、口播文案", "## 二、提词器文案")
    prompter = section(text, "## 二、提词器文案", "## 三、上屏方案")
    spec = parse_md(str(p))
    fs = flat(speech)
    fp = flat(prompter)
    missing_s = []
    missing_p = []
    anchors = []
    for item in spec.get("subs", []):
        anchor = item.get("anchor", "")
        anchors.append(("SUB", anchor))
    for item in spec.get("punch", []):
        anchor = item.get("anchor", "")
        if anchor:
            anchors.append(("PUNCH", anchor))
    for kind, anchor in anchors:
        prefix = "" if kind == "SUB" else "PUNCH:"
        if flat(anchor) not in fs:
            missing_s.append(prefix + anchor)
        if flat(anchor) not in fp:
            missing_p.append(prefix + anchor)
    if missing_s or missing_p:
        print(f"\n{p.parent.name}  口播{count_cn(speech)}字")
        for x in missing_s:
            print("  S缺失:", x)
        for x in missing_p:
            print("  P缺失:", x)
