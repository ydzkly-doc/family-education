#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
素材判序核对 —— 拿到一堆没规范命名的素材时，判断"哪个文件是哪一段"

为什么需要它（2026-09-26 立）：
    手机导出的素材常是 UUID 文件名（如 `8A8A46FC-…MOV`），**名字里没有段序信息**。
    而管道是**按文件名排序当段序**的 → 名字错 = 段落顺序颠倒 + 所有上屏锚点错位。
    ⚠️ 第 2 条就踩过：用户标的 02/03 是**反的**（时间戳顺序对，内容却装反）。

⭐ 判序必须用**两条独立证据**（只用一条会翻车）：
    ① **拍摄时间**：ffmpeg 的 `creation_time` —— ⚠️ 它有**两个值**，
       **第二个才是拍摄时间**（第一个是导出时间，整批文件往往全一样、完全没用）；
    ② **语音识别**：转写每段的**开头 + 结尾**，与文案的分段特征对照
       —— **时间戳只证明"先后"，不证明"文件名 = 段序"**。

用法：
    PY="C:/Users/ZhuanZ/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
    "$PY" 工具脚本/video_check_order.py "…/0N_短标题/_素材"
    "$PY" 工具脚本/video_check_order.py "…/_素材" --head 30 --tail 20
    "$PY" 工具脚本/video_check_order.py "…/_素材" --meta-only   # 只看元数据（几秒，不跑模型）

输出：① 每个文件的时长/分辨率/拍摄时间/音频起点；② 各段开头与结尾的转写；
      ③ 按拍摄时间排序的**建议命名**（人工再用②核对一遍内容，确认后重命名）。
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile

_MODEL = None


def load_paths():
    """优先用技能里解析出的 ffmpeg / whisper 模型（与管道保持同一份）。"""
    skill = os.path.expanduser(r"~/.workbuddy/skills/ffmpeg-vertical-video-pipeline/scripts")
    if os.path.isdir(skill):
        sys.path.insert(0, skill)
        try:
            import paths  # type: ignore
            return paths.ffmpeg_path(), paths
        except Exception:
            pass
    return (shutil.which("ffmpeg") or "ffmpeg"), None


def list_videos(d: str):
    """列出素材（去重、忽略 `_` 开头的产物）。"""
    seen, out = set(), []
    for pat in ("*.MOV", "*.mov", "*.MP4", "*.mp4", "*.MTS", "*.mts", "*.AVI", "*.avi"):
        for p in glob.glob(os.path.join(d, pat)):
            k = os.path.basename(p).lower()
            if k.startswith("_") or k in seen:
                continue
            seen.add(k)
            out.append(p)
    return sorted(out, key=lambda x: os.path.basename(x).lower())


def probe(ffmpeg: str, p: str) -> dict:
    r = subprocess.run([ffmpeg, "-hide_banner", "-i", p],
                       capture_output=True, text=True, errors="replace")
    err = r.stderr
    dur = 0.0
    for ln in err.splitlines():
        if "Duration:" in ln:
            h, m, s = ln.split("Duration:")[1].split(",")[0].strip().split(":")
            dur = int(h) * 3600 + int(m) * 60 + float(s)
            break
    res = re.search(r"(\d{3,4})x(\d{3,4})", err)
    fps = re.search(r"([\d.]+) fps", err)
    ast = re.search(r"Audio:.*?\bstart\s+([\d.]+)", err)
    cts = re.findall(r"creation_time\s*:\s*([0-9T:\-.]+Z)(?:;([0-9T:\-.]+Z))?", err)
    shoot = ""
    if cts:
        shoot = cts[0][1] or cts[0][0]          # ⭐ 第二个值才是拍摄时间
    return {
        "dur": dur,
        "res": ("%sx%s" % res.groups()) if res else "?",
        "fps": fps.group(1) if fps else "?",
        "aud_start": float(ast.group(1)) if ast else 0.0,
        "shoot": shoot,
    }


def transcribe_windows(ffmpeg: str, paths_mod, p: str, dur: float, head: float, tail: float):
    global _MODEL
    from faster_whisper import WhisperModel
    if _MODEL is None:
        mp = paths_mod.resolve_whisper("small") if paths_mod else "small"
        print("载入模型：%s\n" % mp, flush=True)
        _MODEL = WhisperModel(mp, device="cpu", compute_type="int8")
    tmp = tempfile.mkdtemp(prefix="wb_order_")
    out = []
    for tag, ss, t in (("开头", 0.0, head), ("结尾", max(0.0, dur - tail), tail)):
        wav = os.path.join(tmp, "%s.wav" % tag)
        subprocess.run([ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
                        "-ss", "%.2f" % ss, "-t", "%.2f" % t, "-i", p,
                        "-vn", "-ac", "1", "-ar", "16000", wav], check=True)
        segs, _ = _MODEL.transcribe(wav, language="zh", vad_filter=True, beam_size=1)
        out.append((tag, "".join(s.text for s in segs).replace(" ", "").strip()))
    shutil.rmtree(tmp, ignore_errors=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir", help="素材目录")
    ap.add_argument("--head", type=float, default=25.0, help="转写开头多少秒（默认 25）")
    ap.add_argument("--tail", type=float, default=18.0, help="转写结尾多少秒（默认 18）")
    ap.add_argument("--meta-only", action="store_true", help="只看元数据，不跑语音识别")
    a = ap.parse_args()

    d = os.path.abspath(a.dir)
    if not os.path.isdir(d):
        raise SystemExit("❌ 不是目录：%s" % d)
    files = list_videos(d)
    if not files:
        raise SystemExit("❌ 这个目录里没有视频文件：%s" % d)

    ffmpeg, paths_mod = load_paths()
    print("=" * 74)
    print("素材判序核对　目录：%s　共 %d 个文件" % (d, len(files)))
    print("=" * 74)

    metas = []
    for p in files:
        m = probe(ffmpeg, p)
        m["file"] = os.path.basename(p)
        m["path"] = p
        metas.append(m)
        print("--- %s" % m["file"])
        print("    时长 %.1fs ｜ %s ｜ %s fps ｜ 音频起点 %.3fs"
              % (m["dur"], m["res"], m["fps"], m["aud_start"]))
        print("    拍摄时间：%s" % (m["shoot"] or "（读不到）"))
    print("\n素材总时长：%.1f 秒（%.1f 分钟）\n" % (sum(x["dur"] for x in metas),
                                             sum(x["dur"] for x in metas) / 60))

    if not a.meta_only:
        for m in metas:
            print("===== %s" % m["file"], flush=True)
            for tag, txt in transcribe_windows(ffmpeg, paths_mod, m["path"],
                                               m["dur"], a.head, a.tail):
                print("  [%s] %s" % (tag, txt), flush=True)
            print()

    # 建议命名（按拍摄时间；读不到时间的排最后、按原文件名）
    ordered = sorted(metas, key=lambda x: (x["shoot"] == "", x["shoot"], x["file"].lower()))
    print("=" * 74)
    print("按「拍摄时间」排序的建议命名（⚠️ 还要用上面的转写内容核对一遍再改）")
    print("=" * 74)
    for i, m in enumerate(ordered, 1):
        ext = os.path.splitext(m["file"])[1]
        print("  %02d%s   ←  %s   (%.1fs, %s)"
              % (i, ext, m["file"], m["dur"], m["shoot"] or "无时间"))
    print("\n⭐ 判据：**两条证据都指向同一顺序才改名**——时间戳只证明先后，"
          "内容才证明\"这个文件是哪一段\"。")


if __name__ == "__main__":
    main()
