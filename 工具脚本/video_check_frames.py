#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
video_check_frames.py —— 从成片按字幕时间轴抽帧，一眼自查上屏元素。

为什么需要它：管道出片后，"字幕到底上没上、卡片挂对句没有、开头钩子在不在第一帧"——
靠看视频一帧帧找很费劲。本脚本读管道产出的 `.ass`（**含真实时间码，是唯一真相源**），
按样式分组，在**每条出现时长的中点**抽一帧（中点一定处于"正在显示"状态）。

用法：
    python 工具脚本/video_check_frames.py <成片.mp4> <字幕.ass> [--out 目录] [--per-style 3]

      --per-style N   每种样式最多抽几帧（默认 3；按时间序取前 N，**最后一条总会抽**）
      --out DIR       输出目录（默认：ass 同级的 `自查帧/`）
      --ffmpeg PATH   覆盖 ffmpeg（默认识别项目 binaries 下的完整版）

输出：`NN_样式_MMSS.png` ＋ 一张对照表（时间点 / 文件名 / 字幕文本）。
提示：先看 `01_*` 那几张——**开头钩子在第 1 帧**就说明封面可用。
"""
import argparse
import os
import re
import subprocess
import sys

DEFAULT_FFMPEG = r"C:\Users\ZhuanZ\.workbuddy\binaries\ffmpeg\bin\ffmpeg.exe"


def to_sec(s: str) -> float:
    """ASS 时间 H:MM:SS.cc → 秒"""
    m = re.match(r"(\d+):(\d+):(\d+(?:\.\d+)?)", s.strip())
    if not m:
        return 0.0
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


def parse_ass(path: str):
    """读 ASS 的 Dialogue 行 → [{style, start, end, text}]（按时间序）"""
    rows = []
    with open(path, encoding="utf-8-sig") as f:
        for ln in f:
            if not ln.startswith("Dialogue:"):
                continue
            p = ln.split(",", 9)
            if len(p) < 10:
                continue
            text = re.sub(r"\{[^}]*\}", "", p[9]).replace("\\N", " / ").strip()
            rows.append({
                "style": p[3].strip(),
                "start": to_sec(p[1]),
                "end": to_sec(p[2]),
                "text": text,
            })
    rows.sort(key=lambda r: r["start"])
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="成片抽帧自查（按 ASS 时间轴）")
    ap.add_argument("video", help="成片 mp4")
    ap.add_argument("ass", help="管道产出的 .ass")
    ap.add_argument("--out", default=None, help="输出目录（默认 ass 同级 /自查帧）")
    ap.add_argument("--per-style", type=int, default=3, help="每种样式最多抽几帧")
    ap.add_argument("--ffmpeg", default=os.environ.get("WB_FFMPEG", DEFAULT_FFMPEG))
    a = ap.parse_args()

    if not os.path.exists(a.video):
        print(f"❌ 找不到成片：{a.video}")
        return 1
    if not os.path.exists(a.ass):
        print(f"❌ 找不到字幕：{a.ass}")
        return 1

    rows = parse_ass(a.ass)
    if not rows:
        print(f"❌ 没解析到 Dialogue 行：{a.ass}")
        return 1

    out = a.out or os.path.join(os.path.dirname(os.path.abspath(a.ass)), "自查帧")
    os.makedirs(out, exist_ok=True)

    groups = {}
    for r in rows:
        groups.setdefault(r["style"], []).append(r)

    print("=" * 66)
    print(f"  成片：{a.video}")
    print(f"  字幕：{a.ass}（{len(rows)} 条 Dialogue）")
    print(f"  输出：{out}")
    print("=" * 66)

    idx = 0
    for style, items in groups.items():
        pick = items[: a.per_style]
        if len(items) > a.per_style and items[-1] not in pick:
            pick = pick + [items[-1]]
        print(f"\n【{style}】共 {len(items)} 条 → 抽 {len(pick)} 帧")
        for it in pick:
            # 中点抽帧；若这条特别长（>6s），取前 3 秒内的点，避免抽到卡片已消失处
            span = min(it["end"], it["start"] + 6.0)
            t = (it["start"] + span) / 2.0
            idx += 1
            mm, ss = int(t) // 60, int(t) % 60
            name = f"{idx:02d}_{style}_{mm:02d}{ss:02d}.png"
            fp = os.path.join(out, name)
            r = subprocess.run(
                [a.ffmpeg, "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", a.video,
                 "-frames:v", "1", "-q:v", "2", fp],
                capture_output=True)
            ok = os.path.exists(fp) and os.path.getsize(fp) > 0
            print(f"   {'✅' if ok else '❌'} {t:6.1f}s  {name:26s} {it['text'][:32]}")
            if not ok:
                err = r.stderr.decode("utf-8", "ignore")[:150]
                print(f"       抽帧失败：{err}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
