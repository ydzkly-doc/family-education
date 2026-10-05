# -*- coding: utf-8 -*-
"""口播区标点体检（2026-10-05 立：用户点名"不能只用逗号句号"）。

查两类（**结果需人工核**——① 有误报，见下）：
① 该用问号却用了句号：行尾是 。 但句中有疑问词（吗/呢/是不是/有没有/为什么/怎么/哪/谁/多少/几/难道/要不要）。
   ⚠️ **误报来源**：疑问词出现在**陈述句里**也算命中
   （如「先确认人是不是安全，再弄清发生了什么。」「…为什么会发火。」）——需人眼判"这句是不是在问"。
② 承接被句号切断：连续 ≥2 行、每行 ≤14 字、行尾都是 。（读起来一顿一顿，本该用逗号/分号连成一句）。
   ⚠️ **正当例外**（查出来不算错）：**上屏锚点句**（必须独占一行）、**照念台词**（3.4 是设计）、
   **列举的节奏**（3.4）、**板块/段落边界**。

用法：video_script_punct_check.py <文案.md> [...]
"""
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

Q = ("吗", "呢", "是不是", "有没有", "为什么", "怎么", "哪", "谁", "多少", "几", "难道", "要不要")


def oral(t):
    if "## 一、口播文案" not in t:
        return []
    blk = t.split("## 一、口播文案", 1)[1].split("\n## ", 1)[0]
    out = []
    for ln in blk.split("\n"):
        s = ln.strip()
        if not s or s.startswith("【") or s.startswith(">") or s.startswith("#"):
            continue
        out.append(s)
    return out


def main():
    tot = 0
    for md in sys.argv[1:]:
        lines = oral(io.open(md, encoding="utf-8").read())
        name = os.path.basename(md)[:8]
        hits1, hits2 = [], []
        for s in lines:
            if s.endswith("。") and any(w in s for w in Q):
                hits1.append(s)
        run = []
        for s in lines:
            core = re.sub(r"[，。、；：？！]", "", s)
            if s.endswith("。") and len(core) <= 14:
                run.append(s)
            else:
                if len(run) >= 2:
                    hits2.append(run[:4])
                run = []
        if len(run) >= 2:
            hits2.append(run[:4])
        tot += len(hits1) + len(hits2)
        if hits1 or hits2:
            print(f"\n===== {name} =====")
        for h in hits1:
            print(f"  ❓ 疑问句用了句号：{h}")
        for r in hits2:
            print(f"  🔗 连续短句、本该连成一句（{len(r)} 行）：{' ／ '.join(r)}")
    print(f"\n合计待核：{tot}")


if __name__ == "__main__":
    main()
