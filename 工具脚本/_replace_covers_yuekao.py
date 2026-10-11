# -*- coding: utf-8 -*-
"""把月考新封面归位到各条 _成品/：
1) 旧封面备份进 _成品/_旧版本/，加后缀 _旧封面_20261011 前；
2) 新图覆盖 封面_0N.png 与 封面_0N_1x1.png；
3) 逐文件比对大小/存在，输出对账。
不动成片 mp4 / cover.json。
"""
import os
import shutil

BASE = r"D:\个人资料\家庭教育\公众号\第一次月考对话方案\视频号文案"
NEW = os.path.join(BASE, "_新封面_米雾_20261011")
DIRS = {
    "01": "01_出分前忍住别问",
    "02": "02_我不是那块料",
    "03": "03_考好别泼冷水",
    "04": "04_火上来先离开",
    "05": "05_家长会",
}
TAG = "_旧封面_20261011前"

for no, dirname in DIRS.items():
    cg = os.path.join(BASE, dirname, "_成品")
    old_dir = os.path.join(cg, "_旧版本")
    os.makedirs(old_dir, exist_ok=True)
    for kind, name in (("9x16", f"封面_{no}.png"), ("1x1", f"封面_{no}_1x1.png")):
        cur = os.path.join(cg, name)
        # 1) 备份旧封面（仅当存在且尚未备份过）
        stem, ext = os.path.splitext(name)
        bak = os.path.join(old_dir, f"{stem}{TAG}{ext}")
        if os.path.exists(cur) and not os.path.exists(bak):
            shutil.copy2(cur, bak)
            print(f"[backup] {name} -> _旧版本/{os.path.basename(bak)}")
        # 2) 覆盖
        src = os.path.join(NEW, name)
        shutil.copy2(src, cur)
        ok = os.path.getsize(cur) == os.path.getsize(src)
        print(f"[replace] {dirname}/_成品/{name}  size={os.path.getsize(cur)}  match={ok}")
print("done")
