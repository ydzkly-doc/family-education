# -*- coding: utf-8 -*-
# 按新SOP巡检 v4 全33条：竖排异常 / 标签拆字 / 描述长度 / 封面句式 / 版本
import os, re, io, glob

root = r"D:\个人资料\家庭教育\公众号\手机方案\视频号文案_v4"
dirs = sorted([d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d)) and d[:2].isdigit() and not d.startswith("_")],
              key=lambda x: x[:2])

for d in dirs:
    md = glob.glob(os.path.join(root, d, "视频号文案_*.md"))
    if not md:
        print(d, "!! NO MD"); continue
    t = io.open(md[0], encoding="utf-8").read()
    flags = []
    # 竖排异常：出现 > 单字换行 连续多个（朋友圈段）
    if re.search(r"(?:^> .\n){5,}", t, re.M):
        flags.append("竖排异常")
    # 标签拆字：`#` `孩` 这种
    if re.search(r"`#`\s*`孩`|`#`\s*`", t) or re.search(r"`[^`]{1}`\s+`[^`]{1}`\s+`[^`]{1}`", t):
        flags.append("标签拆字")
    # 版本
    mv = re.search(r"\*\*版本\*\*[：:]\s*(.+)", t)
    ver = mv.group(1).strip() if mv else "?"
    # 封面大字
    mc = re.search(r"\*\*封面大字\*\*[：:]\s*(.+)", t)
    cover = mc.group(1).strip() if mc else ""
    # 描述字数
    md2 = re.search(r"\*\*视频描述[^\n]*\*\*\s*\n+\s*>?\s*(.+)", t)
    desc = md2.group(1).strip() if md2 else ""
    # 口播前两句（口播文案后）
    msp = re.search(r"## 一、口播文案\s*(.+?)\n## 二", t, re.S)
    sp = [x.strip() for x in (msp.group(1) if msp else "").splitlines() if x.strip() and not x.strip().startswith("【")][:2]
    print(f"{d[:2]} | 版本={ver[:14]} | 封面={cover[:22]}")
    if flags: print("     ⚠️", "、".join(flags))
