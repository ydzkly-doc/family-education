# -*- coding: utf-8 -*-
"""把新封面（3:4 + 1:1）归位到《改善你的亲子关系》各条 _成品/：
- 旧封面备份进 _成品/_旧版本/封面_0N[_1x1]_旧封面_20261011前.png
- 新图覆盖 _成品/封面_0N.png / 封面_0N_1x1.png，逐张 match 校验
- 成片 mp4 / cover.json 不动（片头卡由 _reburn_heads_gaishan.py 另行重烧）
"""
import os
import shutil

BASE = r"D:\个人资料\家庭教育\公众号\改善你的亲子关系\视频号文案"
SRC = os.path.join(BASE, "_新封面_米雾_20261011")
TAG = "20261011"

DIRS = {
    "01": "01_孩子很听话不等于关系好",
    "02": "02_孩子说随便是他不想说了",
    "03": "03_每句话都对为什么一说就错",
    "04": "04_孩子递过来的是三件事",
    "05": "05_对同事客客气气回家只剩命令",
    "06": "06_一日语言审计四个问题",
    "07": "07_道歉最难的不是对不起",
    "08": "08_旧账说清楚四个动作",
    "09": "09_先修关系会不会把孩子惯坏",
    "10": "10_关系缓和后规则怎么写才能执行",
    "11": "11_情感账户不是交易",
    "12": "12_有些边界不能等关系变好",
}

ok = bad = 0
for no, d in DIRS.items():
    cg = os.path.join(BASE, d, "_成品")
    old_dir = os.path.join(cg, "_旧版本")
    os.makedirs(old_dir, exist_ok=True)
    for src_name, dst_name in (
        (f"封面_{no}.png", f"封面_{no}.png"),
        (f"封面_{no}_1x1.png", f"封面_{no}_1x1.png"),
    ):
        s = os.path.join(SRC, src_name)
        t = os.path.join(cg, dst_name)
        bak = os.path.join(old_dir, dst_name.replace(".png", "_旧封面_%s前.png" % TAG))
        if not os.path.isfile(s):
            print(f"[MISS] {s}")
            bad += 1
            continue
        if os.path.isfile(t) and not os.path.exists(bak):
            shutil.copy2(t, bak)
        shutil.copy2(s, t)
        same = os.path.getsize(s) == os.path.getsize(t)
        ok += 1
        print(f"[{'OK' if same else 'SIZE!'}] {d[:14]} <- {src_name} (备份: {os.path.basename(bak)})")
print(f"done ok={ok} bad={bad}")
