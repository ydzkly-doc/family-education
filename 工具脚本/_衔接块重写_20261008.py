# -*- coding: utf-8 -*-
"""重写各条「系列方案 → 位置与衔接」块为新承接口径。--apply 写盘。"""
import io, os, re, sys, glob
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _承接批量改写_20261008 import BASE, OPEN, CLOSE, find_file

APPLY = "--apply" in sys.argv

for i in range(0, 34):
    num = "%02d" % i
    f = find_file(num)
    t = io.open(f, encoding="utf-8").read()

    # 抓原“发布序”那一行（保留幕名）
    mseq = re.search(r"(- \*\*发布序\*\*：\*\*[^\n]+\n)", t)
    seqline = mseq.group(1) if mseq else "- **发布序**：**%s/33**。\n" % num

    open_line = OPEN.get(num)
    close_line = CLOSE.get(num)

    parts = ["### 位置与衔接\n", seqline.rstrip("\n"),
             "- **承接方式**：**思绪自然承接**（2026-10-08 新口径）——开场从上一话题顺着往下走，落进这一条的问题；⛔ **不设承上句、不设过渡句**，全片不出现“上一条／下一条”这类编号式指代。"]
    if open_line:
        parts.append("- **开场（已写进口播最前）**：\n  > " + open_line)
    if close_line:
        parts.append("- **收尾（已写进口播最后）**：\n  > " + close_line)
    if num == "33":
        parts.append("- 本条是**全系列收尾条**：保留“回望全系列”，但要**讲成一条线**，⛔ 不罗列各条金句。")
    parts.append("- ⛔ **判据不变**：把开场那句和收尾那句都删掉，本条**依然完整**。")
    newblock = "\n".join(parts) + "\n\n"

    # 替换：从“### 位置与衔接”到“### 与相邻条的分工”之前
    pat = re.compile(r"### 位置与衔接.*?(?=### )", re.S)
    if len(pat.findall(t)) != 1:
        raise SystemExit("❌%s 位置与衔接块命中 %d" % (num, len(pat.findall(t))))
    t = pat.sub(lambda _m: newblock, t)

    if APPLY:
        io.open(f, "w", encoding="utf-8").write(t)
    print("✅ %s" % num)

print("\n%s" % ("已写盘" if APPLY else "DRY-RUN"))
