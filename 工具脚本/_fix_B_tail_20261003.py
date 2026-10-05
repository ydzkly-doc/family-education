# -*- coding: utf-8 -*-
'''B 批收尾修正：06 锚点、07 两处超限/劈词、08 大字卡标点开头。'''
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
BASE = r"D:\个人资料\家庭教育\公众号\改善你的亲子关系\视频号文案"
F07 = os.path.join(BASE, "07_道歉最难的不是对不起/视频号文案_07_发布第7条_第4篇_道歉最难的不是对不起.md")
F08 = os.path.join(BASE, "08_旧账说清楚四个动作/视频号文案_08_发布第8条_第4篇_旧账说清楚四个动作.md")
FJ = os.path.join(BASE, "_prompter_args.json")

R = [
    (F07, "我说，昨天我没问清楚，就在饭桌上说你抄作业。",
          "我说，昨天我没问清楚。\n我不该在饭桌上说你抄作业。"),
    (F07, "可这些话一出口，道歉就成了又一次辩解。", "可这些话一出口，就成了辩解。"),
    (F08, "他说的以后先问我，比原谅更实在。", "以后先问我，比原谅更实在。"),
    (FJ, "让他知道，具体要做什么。", "我要让他知道，具体要做什么。"),
]

cache = {}
for p, old, new in R:
    if p not in cache:
        cache[p] = io.open(p, encoding="utf-8").read()
    n = cache[p].count(old)
    if n < 1:
        print("❌ 未命中：", old[:24])
        continue
    cache[p] = cache[p].replace(old, new)
    print("✅ %d 处：%s" % (n, old[:24]))
for p, t in cache.items():
    io.open(p, "w", encoding="utf-8").write(t)
print("已写入", len(cache), "个文件")
