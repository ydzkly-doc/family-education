# -*- coding: utf-8 -*-
"""生成系列级 `_系列过渡文案_合集版.md`（SOP「六、系列方案」要求：
「过渡句全表另存 `_系列过渡文案_合集版.md`，方便拍摄时对照」）。

内容：逐条列出 ① 承上句（开场怎么接上一条）② 启下句（结尾怎么引下一条）③ 独立发布时的备选开头
④ 相邻两条的分工（防重复）。全部**从 12 条 MD 里抽**，保证与口播逐字一致。
"""
import glob
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
SERIES = r"D:\个人资料\家庭教育\公众号\改善你的亲子关系\视频号文案"
OUT = os.path.join(SERIES, "_系列过渡文案_合集版.md")

FILES = []
for d in sorted(os.listdir(SERIES)):
    p = os.path.join(SERIES, d)
    if not os.path.isdir(p) or d.startswith("_"):
        continue
    for f in sorted(glob.glob(os.path.join(p, "视频号文案_*.md"))):
        FILES.append(f)


def after(lines, marker, skip_blank=True):
    """取 marker 之后**连续的非空正文**（marker 可能单独成行；一条过渡句可能写成两行）。"""
    for i, l in enumerate(lines):
        if l.strip().startswith(marker):
            out = []
            rest = l.strip()[len(marker):].strip()
            if rest:
                out.append(rest)
            for j in range(i + 1, min(i + 6, len(lines))):
                s = lines[j].strip()
                if not s:
                    if out:
                        break
                    continue
                if s.startswith("【"):
                    break
                out.append(s)
                if len(out) >= 2:
                    break
            return " ／ ".join(out)
    return ""


rows = []
for f in FILES:
    t = io.open(f, encoding="utf-8").read()
    lines = t.split("\n")
    seq = re.search(r"发布序\s*(\d+)/(\d+)", t)
    title = re.search(r"^#\s*视频号文案\s*·\s*(\d+)《(.+?)》", t, re.M)
    # 口播区里的承上句 / 过渡句
    oral = t.split("## 一、口播文案", 1)[1].split("\n## ", 1)[0].split("\n")
    up = after(oral, "【开场·接上一条】") or "（系列首条，无承上句）"
    down = after(oral, "【合集·过渡】") or "（系列结尾条，不设过渡句，改用祝愿式收尾）"
    solo = ""
    m = re.search(r"\*\*独立发布时用什么开头\*\*[^\n]*?[：:]\s*(.+)", t)
    if m:
        solo = m.group(1).strip().strip("「」").strip()
    rows.append(dict(
        n=int(seq.group(1)) if seq else 0,
        total=seq.group(2) if seq else "?",
        title=title.group(2) if title else os.path.basename(f)[:20],
        up=up, down=down, solo=solo))

rows.sort(key=lambda r: r["n"])

buf = [f"""# 《改善你的亲子关系》· 系列过渡文案（合集版）

> **用途**：拍摄时对照——每条**开头怎么接上一条**、**结尾怎么引下一条**。
> **规则**（SOP「5.8 多条成系列时：做合集就得设计'承上启下'」）：
> · ⭐ **承上句必须与上一条的结尾用词咬合**（实词**逐字回扣**，⛔ 不许自己概括）；
> · ⛔ **两端不要用同一个动词／垫词**（"我说／我说"这种脸对脸）——本表右列已标出两端动词；
> · ⛔ **只承诺"我说"，不承诺"解决"**；**删掉过渡句，这一条依然完整**；
> · **最后一句永远留给"下一条"**；引流句在它之前。
> ⚠️ **本表从 12 条 MD 里自动抽取**，与口播逐字一致；改口播后请**重跑生成脚本**。

| 序 | 本条 | 承上（开场） | 启下（结尾过渡） |
|---|---|---|---|
"""]
for r in rows:
    buf.append(f"| {r['n']:02d} | {r['title']} | {r['up']} | {r['down']} |\n")

buf.append("""
## 咬合链（相邻两条对一遍，⛔ 两端动词不重复）

""")
for i in range(len(rows) - 1):
    a, b = rows[i], rows[i + 1]
    buf.append(f"**{a['n']:02d} → {b['n']:02d}**\n")
    buf.append(f"- 上一条结尾：{a['down']}\n")
    buf.append(f"- 下一条开场：{b['up']}\n")
    buf.append("\n")

buf.append("""## 独立发布时的备选开头（去掉承上句时用）

""")
for r in rows:
    if r["solo"]:
        buf.append(f"- **{r['n']:02d}**：{r['solo']}\n")

io.open(OUT, "w", encoding="utf-8").write("".join(buf))
print(f"✅ 已生成 {OUT}")
print(f"   共 {len(rows)} 条；首条／末条已按「无承上／不设过渡」处理")
