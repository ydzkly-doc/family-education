# -*- coding: utf-8 -*-
"""诊断：区分缺失锚点是『提词器标记符号(【】//)导致』还是真缺失。"""
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

def flat2(text: str) -> str:
    # 额外去掉提词器拍摄标记
    return re.sub(DROP, "", re.sub(r"[【】/／★☆※#]", "", text or ""))

def section(text, start, end):
    m = re.search(re.escape(start) + r"(.*?)" + re.escape(end), text, re.S)
    return m.group(1) if m else ""

for p in sorted(BASE.glob("[0-9][0-9]_*/视频号文案_*.md")):
    text = p.read_text(encoding="utf-8")
    speech = section(text, "## 一、口播文案", "## 二、提词器文案")
    prompter = section(text, "## 二、提词器文案", "## 三、上屏方案")
    spec = parse_md(str(p))
    fs, fp = flat(speech), flat(prompter)
    fs2, fp2 = flat2(speech), flat2(prompter)
    rows = []
    anchors = [("S", x.get("anchor", "")) for x in spec.get("subs", []) if isinstance(x, dict)]
    for x in spec.get("punch", []):
        if x.get("anchor"):
            anchors.append(("P", x["anchor"]))
    real = []
    for kind, a in anchors:
        fa = flat(a)
        ms = fa not in fs
        mp = fa not in fp
        if not (ms or mp):
            continue
        # 标记清理后是否解决
        ms2 = flat2(a) not in fs2
        mp2 = flat2(a) not in fp2
        tag = []
        if ms: tag.append("S" if ms2 else "S*标记")
        if mp: tag.append("P" if mp2 else "P*标记")
        if ms2 or mp2:
            real.append(("+".join(tag), a))
    if real:
        print(f"\n=== {p.parent.name} ===")
        for t, a in real:
            print(f"  [{t}] {a}")
