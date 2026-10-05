# -*- coding: utf-8 -*-
'''人话化 收尾：
  ① 02 上屏句改后 21 字超限 → 换更短的（已 probe：17 字 / 2 行 / 首分句 7）；
  ② _prompter_args.json 里 6 个「分段锚点」与改过的口播同步（01/04/07/09/11/12）。
'''
import argparse
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

BASE = r"D:\个人资料\家庭教育\公众号\改善你的亲子关系\视频号文案"
F02 = "02_孩子说随便是他不想说了/视频号文案_02_发布第2条_第1篇_孩子说随便是他不想说了.md"
JSON = "_prompter_args.json"

R_MD = [
    ("02 上屏句缩短（21→17 字）", F02,
     '''他可以不同意，但该他负的责，还得他自己担。''',
     '''他可以不同意，但责任不能推给我们。'''),
]

R_JSON = [
    ("JSON 01 cuts", "重点不在谁先低头，在你们还有没有一条路，能回到对话里。",
     "重点不在谁先低头，在我们还有没有一条路，能回到对话里。"),
    ("JSON 04 cuts", "他听到的是，我关心的只是问题赶紧消失，不是他刚刚经历了什么。",
     "在孩子听来，我只关心问题赶紧消失，没关心他刚刚经历了什么。"),
    ("JSON 07 cuts", "孩子的受伤，得先理解我的不容易。",
     "孩子受了伤，还得先理解我的不容易。"),
    ("JSON 09 cuts", "规则我说得很完整，关系却没给这场谈话留下入口。",
     "规则我说得很全，可那次，我们根本没谈进去。"),
    ("JSON 11 cuts", "我可以拒绝此刻的建议，但还是要面对自己的责任。",
     "孩子可以不听我的建议，但该负的责任还是得自己负。"),
    ("JSON 12 cuts", "先保证安全，关系才有机会慢慢说。",
     "先把安全保住，关系才有机会慢慢来。"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    texts = {}

    def get(rel):
        p = os.path.join(BASE, rel)
        if p not in texts:
            texts[p] = io.open(p, encoding="utf-8").read()
        return p

    warn = 0
    for label, rel, old, new in R_MD:
        p = get(rel)
        n = texts[p].count(old)
        if n < 1:
            warn += 1
        print(f"{'✅' if n else '❌'} [{label}] 命中 {n} 处")
        if n and not a.dry_run:
            texts[p] = texts[p].replace(old, new)

    pj = get(JSON)
    for label, old, new in R_JSON:
        n = texts[pj].count(old)
        if n < 1:
            warn += 1
        print(f"{'✅' if n else '❌'} [{label}] 命中 {n} 处")
        if n and not a.dry_run:
            texts[pj] = texts[pj].replace(old, new)

    if not a.dry_run:
        for p, t in texts.items():
            io.open(p, "w", encoding="utf-8").write(t)
        print(f"\n已写入 {len(texts)} 个文件")
    print(f"\n未命中 {warn} 处" + ("（--dry-run，未写入）" if a.dry_run else ""))
    return 1 if warn else 0


if __name__ == "__main__":
    sys.exit(main())
