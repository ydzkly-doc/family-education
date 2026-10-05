# -*- coding: utf-8 -*-
'''通顺性修正 第四轮（由 video_script_flow_check.py 抓出）：
  ① 03 —— 上轮改成的两行里，第一行以「，」结尾，提词器会把它当独立行 → 合成一句完整句；
  ② 12 —— 承上句与 11 的过渡句没有逐字回扣（11 是「…有些边界。它们等不了…」，
           12 少了「它们」）→ 让 12 逐字回扣。
'''
import argparse
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

BASE = r"D:\个人资料\家庭教育\公众号\改善你的亲子关系\视频号文案"
F03 = "03_每句话都对为什么一说就错/视频号文案_03_发布第3条_第2篇_每句话都对为什么一说就错.md"
F12 = "12_有些边界不能等关系变好/视频号文案_12_发布第12条_第5篇_有些边界不能等关系变好.md"

R = [
    ("03 悬空逗号行 → 合成一句", F03,
     '''我回来，不是为了他经历了什么，
而是为了证明我当初说对了。''',
     '''我回来，不是为了他经历了什么，而是为了证明我当初说对了。'''),

    ("12 承上句逐字回扣 11 的过渡", F12,
     '''上一条我说，有些边界等不了关系慢慢变好。''',
     '''上一条我说，有些边界，它们等不了关系慢慢变好。'''),
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
