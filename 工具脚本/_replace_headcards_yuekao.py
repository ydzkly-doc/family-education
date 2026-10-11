# -*- coding: utf-8 -*-
"""把重烧好的新封面卡成片归位到 _成品/成片_0N.mp4：
- 新片源：_成品/_旧版本/成片_0N_无封面卡_封面卡.mp4
- 旧的当前成片（带旧封面卡）备份进 _旧版本/成片_0N_旧片头_<tag>.mp4
- 覆盖 _成品/成片_0N.mp4，并重写 .cover.json 时间
- 清理中间产物 _无封面卡_封面卡.mp4 及其 .cover.json
只处理 03/04/05（01/02 已发布不动）。
"""
import os
import json
import datetime
import shutil

BASE = r"D:\个人资料\家庭教育\公众号\第一次月考对话方案\视频号文案"
DIRS = {"03": "03_考好别泼冷水", "04": "04_火上来先离开", "05": "05_家长会"}
TAG = "20261011"

for no, dirname in DIRS.items():
    cg = os.path.join(BASE, dirname, "_成品")
    old_dir = os.path.join(cg, "_旧版本")
    src_new = os.path.join(old_dir, f"成片_{no}_无封面卡_封面卡.mp4")
    target = os.path.join(cg, f"成片_{no}.mp4")
    bak_old = os.path.join(old_dir, f"成片_{no}_旧片头_{TAG}.mp4")

    assert os.path.exists(src_new), f"缺新片源 {src_new}"
    # 1) 备份当前带旧片头的成片
    if not os.path.exists(bak_old):
        shutil.copy2(target, bak_old)
    # 2) 覆盖
    shutil.move(src_new, target)
    # 3) 重写 cover.json
    with open(target + ".cover.json", "w", encoding="utf-8") as fp:
        json.dump({
            "seconds": 2.0,
            "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "note": "正片前的静止封面卡时长；抽帧自查要按它把时间码后移（2026-10-11 换新3:4标准对应的9:16封面卡）",
        }, fp, ensure_ascii=False, indent=1)
    # 4) 清理中间 json（随新片移动后可能残留）
    stray = os.path.join(old_dir, "成片_%s_无封面卡_封面卡.mp4.cover.json" % no)
    if os.path.exists(stray):
        os.remove(stray)
    print(f"[ok] {no}: 覆盖成片_0N.mp4, 旧片头备份={os.path.basename(bak_old)}")
print("done")
