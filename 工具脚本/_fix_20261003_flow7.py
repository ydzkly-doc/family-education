# -*- coding: utf-8 -*-
'''人话化 第七轮：重读一遍后又找出的 5 处（同一条判据：正常人会不会这么说）。
'''
import argparse
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

BASE = r"D:\个人资料\家庭教育\公众号\改善你的亲子关系\视频号文案"
FILES = {
    "01": "01_孩子很听话不等于关系好/视频号文案_01_发布第1条_第1篇_孩子很听话不等于关系好.md",
    "03": "03_每句话都对为什么一说就错/视频号文案_03_发布第3条_第2篇_每句话都对为什么一说就错.md",
    "05": "05_对同事客客气气回家只剩命令/视频号文案_05_发布第5条_第3篇_对同事客客气气回家只剩命令.md",
    "06": "06_一日语言审计四个问题/视频号文案_06_发布第6条_第3篇_一日语言审计四个问题.md",
    "07": "07_道歉最难的不是对不起/视频号文案_07_发布第7条_第4篇_道歉最难的不是对不起.md",
}

R = [
    ("01 「我听见的是他自己」——听见≠听出来", "01",
     '''他真想自己试的时候，我听见的是他自己，还是"不领情"。''',
     '''他真想自己试的时候，我听出来的是他想长大，还是"不领情"。'''),

    ("03 「变了意思」与下一句「只剩一个意思」撞词", "03",
     '''慢慢它就变了意思。''',
     '''慢慢它就变了味。'''),

    ("05 「把亲密当成一种天然的权限」——太书面，且是本条论点句", "05",
     '''恰恰是家太熟、关系太近，我们容易把亲密，当成一种天然的权限。''',
     '''恰恰是家太熟、关系太近，我们容易觉得，亲近就不用讲究了。'''),

    ("06 「要处理什么」——「处理」抽象", "06",
     '''让他知道，具体要处理什么。''',
     '''让他知道，具体要做什么。'''),

    ("07 「方向是先修复旧账」——「方向」是文件用词", "07",
     '''课里讲到关系已经透支的时候，方向是先修复旧账。''',
     '''课里讲到，关系透支了，要先把旧账修好。'''),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    files = {}
    warn = 0
    for label, key, old, new in R:
        p = os.path.join(BASE, FILES[key])
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
