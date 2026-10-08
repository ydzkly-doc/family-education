# -*- coding: utf-8 -*-
"""清理 07-12 各条 `_过程文件/` 与 `_成品/_过程文件/` 里的**诊断产物**。

保留（交付/留痕/可复用）：
  `covercard_0.png`（封面卡第 0 帧核验图）、`合成日志_*.txt`、`素材判序.md`、`说明.txt`
  `cover.png` / `cover_1x1.png` / `subs.ass` / `timings.json` / `bd.rnnn` / `_cover*.ass`

清理：
  `_t{NN}_*`（测光抽帧）、`chk_*`（锚点核验帧）、`取帧候选.png`（取帧对比图）、`_cand/`（其临时帧）、
  以及 07 遗留的 `covercard_0_fixed.png`（旧的，已被重抽的 covercard_0.png 取代）

用法：python _clean_workdir.py [--dry-run] 07 08 09 ...
"""
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")
PY = r"C:/Users/ZhuanZ/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
TRASH = r"D:/个人资料/家庭教育/工具脚本/trash_to_recycle.py"
BASE = r"D:/个人资料/家庭教育/公众号/改善你的亲子关系/视频号文案"

KEEP = {"covercard_0.png", "素材判序.md", "说明.txt",
        "cover.png", "cover_1x1.png", "subs.ass", "timings.json", "bd.rnnn",
        "_cover.ass", "_cover_1x1.ass",
        # 管道中间产物 —— 01–06 各条**都保留着**（各约 300 MB），按既有惯例不动它们
        "_stage0_join.mp4", "_stage1_cut.mp4", "_bgm_mix.wav"}
KEEP_PREFIX = ("合成日志",)


def junk_in(d, seq):
    """列出该目录里**该清理**的文件（白名单式：只删诊断产物，其余一律保留）。"""
    out = []
    for f in os.listdir(d):
        p = os.path.join(d, f)
        if os.path.isdir(p):
            if f == "_cand":
                out.append(p)
            continue
        if f in KEEP:
            continue
        if any(f.startswith(k) for k in KEEP_PREFIX):
            continue
        # 到这里的都是"非保留项"：_t{NN}_*（测光抽帧）、chk_*（锚点核验帧）、
        # 取帧候选.png、covercard_0_fixed.png 等诊断产物
        out.append(p)
    return out


def main():
    dry = "--dry-run" in sys.argv
    seqs = [a for a in sys.argv[1:] if not a.startswith("-")] or \
           ["07", "08", "09", "10", "11", "12"]
    import ctypes
    from ctypes import wintypes, Structure, byref, sizeof, c_ulonglong

    alljunk = []
    for seq in seqs:
        dirs = [x for x in os.listdir(BASE) if x.startswith(seq + "_")]
        if not dirs:
            print("⚠️ %s：找不到条目目录" % seq)
            continue
        root = os.path.join(BASE, dirs[0])
        for sub in (os.path.join(root, "_过程文件"),
                    os.path.join(root, "_成品", "_过程文件")):
            if not os.path.isdir(sub):
                continue
            j = junk_in(sub, seq)
            if j:
                print("%s / %s → %d 个" % (seq, os.path.relpath(sub, root), len(j)))
                for p in sorted(j):
                    print("     ", os.path.basename(p))
                alljunk += j
    print("\n合计 %d 个" % len(alljunk))
    if dry or not alljunk:
        return 0
    p = subprocess.run([PY, TRASH] + alljunk, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    print((p.stdout or "")[-1500:])
    return 0


if __name__ == "__main__":
    sys.exit(main())
