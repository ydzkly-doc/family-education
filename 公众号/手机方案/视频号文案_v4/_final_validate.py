# -*- coding: utf-8 -*-
"""最终全量校验：parse 成功 / title_persist=True / bgm 存在 / 所有 subs+punch 锚点在口播与提词器中 missing=[] / 口播字数。"""
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, r"D:\个人资料\家庭教育\_技能\ffmpeg-vertical-video-pipeline\scripts")
from md_spec import parse_md  # noqa: E402

DROP = r"[\s，。？！、；：「」『』“”\"'（）()≠=·…—\-—:：]+"

def flat(t):
    return re.sub(DROP, "", t or "")

def section(text, a, b):
    m = re.search(re.escape(a) + r"(.*?)" + re.escape(b), text, re.S)
    return m.group(1) if m else ""

def cn_count(t):
    return len(re.findall(r"[\u4e00-\u9fffA-Za-z0-9]", t))

rows = []
all_ok = True
for p in sorted(BASE.glob("[0-9][0-9]_*/视频号文案_*.md")):
    name = p.parent.name
    problems = []
    try:
        spec = parse_md(str(p))
    except Exception as e:
        rows.append((name, "PARSE_FAIL", 0, str(e)))
        all_ok = False
        continue
    text = p.read_text(encoding="utf-8")
    speech = section(text, "## 一、口播文案", "## 二、提词器文案")
    prompt = section(text, "## 二、提词器文案", "## 三、上屏方案")
    fs, fp = flat(speech), flat(prompt)

    tp = spec.get("title_persist")
    if not tp:
        problems.append("无title_persist")
    elif (tp.get("color") or "").upper() != "#6E97C9":
        problems.append(f"标题色={tp.get('color')}")
    if not spec.get("bgm"):
        problems.append("无bgm")

    miss_s, miss_p = [], []
    anchors = [("s", x.get("anchor", "")) for x in spec.get("subs", []) if isinstance(x, dict)]
    for x in spec.get("punch", []) or []:
        if x.get("anchor"):
            anchors.append(("p", x["anchor"]))
    for _, a in anchors:
        fa = flat(a)
        if fa not in fs:
            miss_s.append(a)
        if fa not in fp:
            miss_p.append(a)
    if miss_s:
        problems.append("S缺:" + "/".join(miss_s))
    if miss_p:
        problems.append("P缺:" + "/".join(miss_p))
    if problems:
        all_ok = False
    rows.append((name, "OK" if not problems else "FAIL", cn_count(speech), "；".join(problems)))

print(f"{'目录':<34}{'结果':<5}{'口播字数':<6}问题")
for name, st, n, msg in rows:
    print(f"{name:<34}{st:<6}{n:<7}{msg}")

print("\n字数区间检查（常规360-520，00约300-340）：")
for name, st, n, msg in rows:
    if name.startswith("00"):
        flag = "" if 300 <= n <= 340 else "  <-- 00越界"
    else:
        flag = "" if 360 <= n <= 520 else "  <-- 越界"
    if flag:
        print(f"  {name}: {n}{flag}")

print("\n全部通过 ✅" if all_ok else "\n仍有失败 ❌")
sys.exit(0 if all_ok else 1)
