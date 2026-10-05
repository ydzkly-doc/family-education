# -*- coding: utf-8 -*-
"""收尾修正：09 的标色词同步 ＋ 10 的分段锚点同步（改句必改引用，SOP 3.15 那条）。"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
BASE = r"D:\个人资料\家庭教育\公众号\改善你的亲子关系\视频号文案"
F09 = os.path.join(BASE, "09_先修关系会不会把孩子惯坏/视频号文案_09_发布第9条_第5篇_先修关系会不会把孩子惯坏.md")

t = io.open(F09, encoding="utf-8").read()
R9 = [
    ("09 强调句4 标色", '「不能因为他说等一等，就一直不动。」 → "不行动的理由"标暖色加粗',
     '「不能因为他说等一等，就一直不动。」 → "一直不动"标暖色加粗'),
    ("09 全片标色", '- "共情不是同意"、"不行动的理由" → 暖色加粗',
     '- "共情不是同意"、"一直不动" → 暖色加粗'),
]
bad = 0
for label, old, new in R9:
    n = t.count(old)
    if n == 0:
        print(f"❌ {label}：0 处")
        bad += 1
        continue
    t = t.replace(old, new)
    print(f"✅ {label}：{n} 处")
io.open(F09, "w", encoding="utf-8").write(t)

# 10 的分段锚点：句子改过，引用必须一起改（否则 gen_prompter 直接报"锚点找不到"）
jp = os.path.join(BASE, "_prompter_args.json")
items = json.load(io.open(jp, encoding="utf-8"))
old_cut = "如果两个人说出来的意思不一样，那后面的冲突，多半只是把那个模糊的约定重新吵一遍。"
new_cut = "如果两个人说出来的意思不一样，那后面的冲突，多半只是把那个约定，重新吵一遍。"
hit = 0
for it in items:
    for i, c in enumerate(it["cuts"]):
        if c == old_cut:
            it["cuts"][i] = new_cut
            hit += 1
if hit:
    io.open(jp, "w", encoding="utf-8").write(
        json.dumps(items, ensure_ascii=False, indent=2) + "\n")
    print(f"✅ 10 分段锚点：{hit} 处")
else:
    print("❌ 10 分段锚点：0 处")
    bad += 1

print()
print("全部通过 ✅" if not bad else f"⚠️ {bad} 处需人工看")
sys.exit(1 if bad else 0)
