#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
重抽「逐字稿」：从文案 MD 的「二、口播文案」区，重生成同目录的 `<MD名>_文案.txt`。

为什么要它（2026-10-02 立）：
    管道跑 `--md` 时**会自动抽** txt（`video_make.py` → `md_spec.extract_script`），
    但那只在"**合成的时候**"发生 —— 改完口播到下次合成之间，**txt 还是旧的**。
    实测：05/06 的 txt 停在 09-30，而 MD 在 10-02 改过三轮；谁要是直接
    `--script 文案.txt`，用的就是旧稿（而且不会有任何报错）。
    → **改完口播就顺手跑一遍这个**，txt 立刻与 MD 对齐。

⛔ 不要手工编辑 txt（它是 MD 的派生物，手改必然再次失同步）。

用法：
    PY="C:/Users/ZhuanZ/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
    "$PY" 工具脚本/重抽逐字稿_refresh_script.py <文案.md 或 目录>
    "$PY" 工具脚本/重抽逐字稿_refresh_script.py <…> --check   # 只看差异，不写
"""
import argparse
import glob
import os
import sys

SKILL_SCRIPTS = os.path.expanduser(
    "~/.workbuddy/skills/ffmpeg-vertical-video-pipeline/scripts")
sys.path.insert(0, SKILL_SCRIPTS)
sys.stdout.reconfigure(encoding="utf-8")

try:
    import md_spec          # ⭐ 用技能里的抽取函数，保证与管道同一口径
except ImportError as e:      # pragma: no cover
    raise SystemExit(f"⛔ 找不到技能的 md_spec（{SKILL_SCRIPTS}）：{e}")


def targets(path: str):
    if os.path.isdir(path):
        return sorted(p for p in glob.glob(os.path.join(path, "**", "视频号文案_*.md"),
                                           recursive=True)
                      if not os.path.basename(p).startswith("_"))
    return [path]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="文案 md 或目录")
    ap.add_argument("--check", action="store_true", help="只比对，不写入")
    a = ap.parse_args()

    files = targets(a.target)
    if not files:
        print("没找到 `视频号文案_*.md`")
        return 1

    changed = same = 0
    for md in files:
        txt = md_spec.extract_script(md)
        if not txt.strip():
            print(f"  ⚠️  {os.path.basename(md)}：口播区抽不出内容（跳过）")
            continue
        out = os.path.splitext(os.path.abspath(md))[0] + "_文案.txt"
        old = ""
        if os.path.isfile(out):
            with open(out, encoding="utf-8") as f:
                old = f.read()

        def norm(s):
            return [x for x in s.replace("\r", "").split("\n") if x.strip()]

        if norm(old) == norm(txt):
            same += 1
            print(f"  ✅ 一致  {os.path.basename(out)}（{len(txt.replace(chr(10), ''))} 字）")
            continue
        changed += 1
        print(f"  ✳️  需更新 {os.path.basename(out)}："
              f"{len(norm(old))} 行 → {len(norm(txt))} 行"
              f"（{len(txt.replace(chr(10), ''))} 字）")
        if not a.check:
            with open(out, "w", encoding="utf-8") as f:
                f.write(txt + "\n")

    print(f"\n{'（--check 未写入）' if a.check else '已写入'}"
          f"：需更新 {changed} 个，已一致 {same} 个")
    return 0


if __name__ == "__main__":
    sys.exit(main())
