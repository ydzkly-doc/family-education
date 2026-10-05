# -*- coding: utf-8 -*-
'''通顺性修正 第二轮（2026-10-03）：
  ① 06 四问统一成疑问句（首轮加「看」字后 18/15 字越出折行判据 [总-10, 10]）；
  ② 05 上屏方案的两句锚点与口播同步（首轮只改了口播，上屏仍是旧的「你/我」）。
'''
import argparse
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

BASE = r"D:\个人资料\家庭教育\公众号\改善你的亲子关系\视频号文案"
F05 = "05_对同事客客气气回家只剩命令/视频号文案_05_发布第5条_第3篇_对同事客客气气回家只剩命令.md"
F06 = "06_一日语言审计四个问题/视频号文案_06_发布第6条_第3篇_一日语言审计四个问题.md"

R = [
    # 06：四个问题统一为「第N个，……？」（自问语感），且都 ≤14 字 → 折行判据通过
    ("06 四问之一·改疑问", F06,
     '''第一个，看命令里有没有信息。''',
     '''第一个，命令里有没有信息？'''),
    ("06 四问之二·改疑问", F06,
     '''第二个，看我要求之前，有没有教过他。''',
     '''第二个，我要求之前教过他吗？'''),
    ("06 四问之三·改疑问", F06,
     '''第三个，看规则是不是临时加的。''',
     '''第三个，规则是不是临时加的？'''),
    ("06 四问之四·改疑问", F06,
     '''第四个，看我有没有当众揭短。''',
     '''第四个，我有没有当众揭短？'''),

    # 05：上屏方案 + 录制提示 里的两句锚点，必须与口播逐字一致
    ("05 上屏锚点同步(前)", F05,
     '''我刚进门，你先看见地上的书包。''',
     '''他刚进门，我先看见地上的书包。'''),
    ("05 上屏锚点同步(后)", F05,
     '''我想说今天的事，你已经列了四件。''',
     '''他想说今天的事，我已经列了四件。'''),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    files = {}
    warn = 0
    for label, rel, old, new in R:
        p = os.path.join(BASE, rel)
        if p not in files:
            files[p] = io.open(p, encoding="utf-8").read()
        n = files[p].count(old)
        if n < 1:
            warn += 1
        print(f"{'✅' if n else '❌'} [{label}] 命中 {n} 处")
        if n and not a.dry_run:
            files[p] = files[p].replace(old, new)

    if not a.dry_run:
        for p, t in files.items():
            io.open(p, "w", encoding="utf-8").write(t)
    print(f"\n未命中 {warn} 处" + ("（--dry-run，未写入）" if a.dry_run else ""))
    return 1 if warn else 0


if __name__ == "__main__":
    sys.exit(main())
