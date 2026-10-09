# -*- coding: utf-8 -*-
import subprocess, sys
PY = r"C:/Users/ZhuanZ/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
ROOT = r"D:/个人资料/家庭教育"
GEN = ROOT + r"/工具脚本/gen_prompter.py"
BASE = ROOT + r"/公众号/第一次月考对话方案/视频号文案"

JOBS = {
 "02": (r"02_我不是那块料/视频号文案_02_我不是那块料.md",
   ["不是「这个人」的标价。",
    "第二步，把人和事分开。"],
   ["第 1 段拍（“我不是那块料”是下定义）",
    "第 2 段拍（当教练不当裁判、先接情绪）",
    "第 3 段拍（人和事分开、引到具体科、关房间、安全与落点）"]),
 "04": (r"04_火上来先离开/视频号文案_04_火上来先离开.md",
   ["是先给身体一个动作。",
    "「你上次就这样」这种话，一出口全完。"],
   ["第 1 段拍（火上来别硬忍，给动作）",
    "第 2 段拍（三步：离开-喝水-说事）",
    "第 3 段拍（怪别人站队、老人挡枪、满不在乎与落点）"]),
}

check = "--check" in sys.argv
for n, (rel, cuts, titles) in JOBS.items():
    cmd = [PY, GEN, BASE + "/" + rel,
           "--cuts", "||".join(cuts), "--titles", "||".join(titles)]
    if check:
        cmd.append("--check")
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    print("====", n, "returncode", p.returncode)
    print(p.stdout.strip())
    if p.returncode:
        print(p.stderr.strip())
