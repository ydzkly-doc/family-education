# -*- coding: utf-8 -*-
'''C 批收尾：09/10 锚点同步、11 钩子与封面折行。'''
import io
import os
import sys
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"D:\个人资料\家庭教育\公众号\改善你的亲子关系\视频号文案"
F11 = os.path.join(BASE, "11_情感账户不是交易/视频号文案_11_发布第11条_第2篇_情感账户不是交易.md")
FJ = os.path.join(BASE, "_prompter_args.json")

R = [
    (FJ, "把三件事挤在情绪最高点里，剩下的就只有争输赢了。", "三件事全在气头上谈，最后只剩吵谁对谁错。"),
    (FJ, "如果两个人说出来的意思不一样，那后面的冲突，多半只是把那个约定，重新吵一遍。",
         "如果两个人说的不是一回事，那后面的冲突，多半只是把那个约定，重新吵一遍。"),
    (F11, "情感账户，为什么不是一笔交易？", "情感账户不是交易，那是什么？"),
]
cache = {}
for p, old, new in R:
    if p not in cache:
        cache[p] = io.open(p, encoding="utf-8").read()
    n = cache[p].count(old)
    if n < 1:
        print("❌ 未命中：", old[:26]); continue
    cache[p] = cache[p].replace(old, new)
    print("✅ %d 处：%s" % (n, old[:26]))
for p, t in cache.items():
    io.open(p, "w", encoding="utf-8").write(t)
print("已写入", len(cache), "个文件")
