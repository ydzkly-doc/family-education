# -*- coding: utf-8 -*-
"""《改善你的亲子关系》12 条：重烧片头 2 秒封面卡（9:16 新标准卡）。
- 源＝各条 _成品/_旧版本/成片_0N_无封面卡.mp4（正片）
- 卡＝_新封面_米雾_20261011/片头卡9x16/封面卡_0N_9x16.png
- 调 video_add_cover_card.py（码率自动沿用），产物 成片_0N_无封面卡_封面卡.mp4
- 归位：旧带卡成片备份 成片_0N_旧片头_20261011.mp4 → 新片覆盖 _成品/成片_0N.mp4 → 重写 cover.json
"""
import datetime
import json
import os
import shutil
import subprocess
import sys

ROOT = r"D:\个人资料\家庭教育"
BASE = os.path.join(ROOT, "公众号", "改善你的亲子关系", "视频号文案")
COVER_DIR = os.path.join(BASE, "_新封面_米雾_20261011", "片头卡9x16")
PY = os.path.join(ROOT, "..", "..", "..", ".workbuddy", "binaries", "python", "envs", "default", "Scripts", "python.exe")
PY = r"C:\Users\ZhuanZ\.workbuddy\binaries\python\envs\default\Scripts\python.exe"
ADD = os.path.join(ROOT, "工具脚本", "video_add_cover_card.py")
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

only = sys.argv[1:] or list(DIRS)
for no in only:
    d = DIRS[no]
    cg = os.path.join(BASE, d, "_成品")
    old_dir = os.path.join(cg, "_旧版本")
    src = os.path.join(old_dir, f"成片_{no}_无封面卡.mp4")
    card = os.path.join(COVER_DIR, f"封面卡_{no}_9x16.png")
    target = os.path.join(cg, f"成片_{no}.mp4")
    bak_old = os.path.join(old_dir, f"成片_{no}_旧片头_{TAG}.mp4")
    new = os.path.join(old_dir, f"成片_{no}_无封面卡_封面卡.mp4")
    for p in (src, card):
        if not os.path.isfile(p):
            print(f"[MISS] {no}: {p}")
            continue
    print(f"=== {no} 重烧片头 ===", flush=True)
    r = subprocess.run([PY, ADD, src, "--cover-image", card, "--seconds", "2"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0 or not os.path.isfile(new):
        print(f"[FAIL] {no}: video_add_cover_card 退出码 {r.returncode}")
        print((r.stdout or "")[-500:])
        print((r.stderr or "")[-800:])
        continue
    if not os.path.exists(bak_old):
        shutil.copy2(target, bak_old)
    shutil.move(new, target)
    stray = new + ".cover.json"
    if os.path.exists(stray):
        os.remove(stray)
    with open(target + ".cover.json", "w", encoding="utf-8") as fp:
        json.dump({
            "seconds": 2.0,
            "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "note": "正片前的静止封面卡时长；抽帧自查要按它把时间码后移（2026-10-11 换新封面标准 9:16 片头卡）",
        }, fp, ensure_ascii=False, indent=1)
    print(f"[OK] {no}: 新片头已归位，旧片头备份 {os.path.basename(bak_old)}", flush=True)
print("done")
