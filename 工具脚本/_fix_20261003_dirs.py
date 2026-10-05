# -*- coding: utf-8 -*-
"""补齐 12 个条目录的标准结构（SOP「输出规范 → 目录结构」）。

原来缺什么（用户 2026-10-03 对照旧系列发现）：
    《改善你的亲子关系》的 12 个条目录**只有那个 .md**，缺了三个下划线工作区：
      `_素材/`（输入）／`_成品/`（交付）／`_过程文件/`（中间产物，可随时删）。
    → 本脚本按 SOP 建齐，并在每个目录放一份 `说明.txt`：
      ① 空目录 git 不跟踪，放个真文件才留得住；
      ② 这三个目录将来是"拍摄的人 / 合成的人"第一眼要看的地方，说明写在这里最省事。

⛔ 不覆盖已存在的目录或文件（幂等）。
用法：
    PY="C:/Users/ZhuanZ/.workbuddy/binaries/python/versions/3.13.12/python.exe"
    "$PY" 工具脚本/_fix_20261003_dirs.py [--dry-run]
"""
import argparse
import glob
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

SERIES = r"D:\个人资料\家庭教育\公众号\改善你的亲子关系\视频号文案"

SU = """【这一个目录放什么】
分段拍摄的口播素材。文件名顺序 = 段序（01.mp4 02.mp4 03.mp4…）。
按本条文案「二、提词器文案」里的 `——第 N 段拍——` 分段，几段就几个文件。

【拍摄前必看】
1. 竖屏 1080×1920 原画（低于这个尺寸后期要放大，画面变软）。
2. 分段拍，每段 60~110 秒；段数 2~3 段（服从语意断点，别硬凑）。
3. 说错了就**整段重录**——⛔ 别在同一段里把那一句重说一遍（两句都会留在片子里）。
4. 每段开头停 1~2 秒再开口，说完再停 1 秒。
5. 全程不动机位／背景／灯（跨次补拍尤其要命：位置跳变后期修不了）。
6. 脸朝着光，别背对窗户；人物放在画面下 2/3，**头顶留出 1/3** 给字幕和卡片。
7. 素材没命名时（手机导出常是 UUID 名）：用 `工具脚本/video_check_order.py` 判序——
   拍摄时间 ＋ 语音识别**两条证据都指向同一顺序**，才改名为 `01.MOV…`。

【⛔ 音乐不要放这里】
BGM 放 `_资产/bgm/`，别扔进 `_素材/` 根目录（会被当素材误扫）。
"""

CHENG = """【交付物都在这里】
- `成片_NN.mp4`
- `封面_NN.png`（9:16）
- `封面_NN_1x1.png`（1:1，发朋友圈用）

【怎么跑】
见本条文案的「四、视频合成方案」；`--out` 一律指向本目录。
⚠️ 管道把封面**写死在** `条目录/_过程文件/`，跑完要手动 copy 两张进来。
"""

GUO = """【管道中间产物，可随时删】
`_stage*.mp4` / `subs.ass` / `timings.json` / `preview.ass` / 自查帧/ …

⚠️ 但有两样核对时要用：
- `timings.json` —— 核时间码、补 BGM 时要**整体 +2.0 秒**（成片前置过 2 秒封面卡）
- `preview.ass` —— 核「标点开头的第二行 / 词被劈开」（**只看落点表发现不了**）
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    dirs = sorted(d for d in os.listdir(SERIES)
                  if os.path.isdir(os.path.join(SERIES, d)) and not d.startswith("_"))
    n_dir = n_file = 0
    for d in dirs:
        for sub, txt in (("_素材", SU), ("_成品", CHENG), ("_过程文件", GUO)):
            p = os.path.join(SERIES, d, sub)
            f = os.path.join(p, "说明.txt")
            if a.dry_run:
                print(f"  {'✓' if os.path.isdir(p) else '+'} {d}/{sub}")
                continue
            os.makedirs(p, exist_ok=True)
            n_dir += 1
            if not os.path.exists(f):
                io.open(f, "w", encoding="utf-8").write(txt)
                n_file += 1
    print(f"\n{len(dirs)} 个条目录：处理 {n_dir} 个子目录，新建说明 {n_file} 个"
          + ("（--dry-run，未写入）" if a.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
