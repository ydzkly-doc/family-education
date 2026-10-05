# -*- coding: utf-8 -*-
"""一次性检查：把「三、上屏方案」里的**锚点句**（强调句 ＋ 挂句），
逐条对着「一、口播文案」核「逐字存在、且独占一行」。

用法：_chk_anchors.py <文案.md> [...]
说明：
  · **卡面文字**（大字卡/浅底卡的第一段「…」）**不要求**出现在口播里——那是卡片上写的字，
    时间码看「挂在这句」；所以本脚本只核**强调句**与**挂句**。
判据：锚点句必须是口播里的**某一整行**，否则渲染时挂不上（会退化成整行起点或直接失败）。
"""
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")


def section(t, name):
    if f"## {name}" not in t:
        return ""
    return t.split(f"## {name}", 1)[1].split("\n## ", 1)[0]


def sub(t, name):
    """取 ### name 到下一个 ### 之间"""
    if f"### {name}" not in t:
        return ""
    return t.split(f"### {name}", 1)[1].split("\n### ", 1)[0]


def anchors(up):
    items = []
    for ln in sub(up, "强调句").split("\n"):
        m = re.match(r"^\d+\.\s*「(.+?)」", ln.strip())
        if m:
            items.append(("强调句", m.group(1).strip()))
    for sec in ("金句大字卡（居中）", "浅底卡（画面下方浅底文字卡）"):
        for ln in sub(up, sec).split("\n"):
            s = ln.strip()
            m = re.match(r"^-\s*挂在这句：「(.+?)」", s)
            if m:
                items.append((sec[:4] + "挂句", m.group(1).strip()))
            m2 = re.search(r"挂在(?:这句)?「(.+?)」", s)
            if m2 and not m:
                items.append((sec[:4] + "挂句", m2.group(1).strip()))
    return items


def main():
    bad_total = 0
    for md in sys.argv[1:]:
        t = io.open(md, encoding="utf-8").read()
        oral = section(t, "一、口播文案")
        lines = [l.strip() for l in oral.split("\n") if l.strip()]
        lineset = set(lines)
        print(f"\n=== {os.path.basename(md)} ===")
        bad = 0
        for kind, sent in anchors(section(t, "三、上屏方案")):
            if sent in lineset:
                continue
            bad += 1
            where = "在口播里，但没独占一行" if any(sent in l for l in lines) else "口播里找不到"
            print(f"  ❌ [{kind}] {where}：{sent}")
        print(f"  ✅ {len(anchors(section(t, '三、上屏方案')))} 处锚点全部逐字命中、各占一行"
              if bad == 0 else f"  ⚠️ {bad} 处对不上")
        bad_total += bad
    print(f"\n合计问题：{bad_total}")
    return 1 if bad_total else 0


if __name__ == "__main__":
    sys.exit(main())
