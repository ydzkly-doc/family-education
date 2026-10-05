# -*- coding: utf-8 -*-
r"""
BGM 音色探针 —— 量几个声学特征，用于「像不像钢琴」的**相对**判断。

⛔ **为什么是"相对"而不是"识别"**：从音频里**无法可靠地识别乐器**。
   能做的只有：拿**已知是钢琴的那一首**当参照，看别的曲子离它近还是离"大自然音效"近。
   → 结果一律标注为**推测**，最终以人耳为准。绝不把推测写成结论。

三个特征（都是逐帧算、再取统计量）：

| 特征 | 含义 | 钢琴（独奏） | 氛围/大自然 |
|---|---|---|---|
| **谱质心** centroid | 频谱"重心"频率，越亮越大 | 中高频、随音符起伏 | 常偏低、平稳 |
| **谱平坦度** flatness | 0＝纯音/谐波，1＝白噪声 | 低（谐波丰富） | 偏高（水声/风声/沙沙声） |
| **起音对比度** flux_p90/flux_median | 谱通量的峰值/中位 → "有没有一颗颗的音符" | **高**（一个个音） | **低**（连续不断） |

用法：
  python 工具脚本/bgm_timbre_probe.py --dir "BGM" --secs 60 \
      --piano "传递的温柔（无损钢琴曲）-安静轻音.mp3" \
      --nature "【大自然韵律】鸟儿欢快的鸣叫大自然解压放松音乐.mp3"
"""
from __future__ import annotations

import argparse
import os
import re
import statistics
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

FF = os.path.join(os.path.expanduser("~"),
                  ".workbuddy", "binaries", "ffmpeg", "bin", "ffmpeg.exe")
AUDIO_EXTS = (".mp3", ".m4a", ".aac", ".wav", ".flac", ".ogg", ".opus", ".wma")
MEASURES = ("centroid", "flatness", "flux")


def probe(path: str, secs: float, start: float, workdir: str) -> dict:
    """跑一遍 ffmpeg，取三个特征的逐帧序列 → 统计量"""
    tiles = "+".join(MEASURES)
    chain = [f"aspectralstats=measure={tiles}"]
    files = {}
    for m in MEASURES:
        fn = f"_sp_{m}.txt"
        files[m] = os.path.join(workdir, fn)
        if os.path.exists(files[m]):
            os.remove(files[m])
        chain.append(f"ametadata=print:key=lavfi.aspectralstats.1.{m}"
                     f":file={fn}")
    p = subprocess.run(
        [FF, "-hide_banner", "-y", "-ss", f"{start}", "-t", f"{secs}",
         "-i", os.path.abspath(path),
         "-af", ",".join(chain), "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=workdir)
    out = {}
    for m in MEASURES:
        vals = []
        if os.path.isfile(files[m]):
            for ln in open(files[m], encoding="utf-8", errors="replace"):
                mm = re.search(rf"aspectralstats\.1\.{m}=(-?[\d.]+|-?inf)", ln)
                if mm:
                    v = mm.group(1)
                    if "inf" not in v:
                        vals.append(float(v))
        out[m] = vals
    if not out["centroid"]:
        return {}
    flux = out["flux"]
    med = statistics.median(flux) if flux else 0.0
    p90 = sorted(flux)[int(len(flux) * 0.9)] if flux else 0.0
    return {
        "centroid": statistics.mean(out["centroid"]),
        "flatness": statistics.mean(out["flatness"]) if out["flatness"] else float("nan"),
        "flux_med": med,
        "flux_p90": p90,
        "flux_ratio": (p90 / med) if med > 1e-9 else float("inf"),
        "frames": len(out["centroid"]),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="BGM 音色探针（相对判断）")
    ap.add_argument("--dir", required=True)
    ap.add_argument("--secs", type=float, default=60.0, help="每首取多少秒")
    ap.add_argument("--start", type=float, default=60.0, help="从第几秒起取")
    ap.add_argument("--piano", help="已知钢琴曲的文件名（参照）")
    ap.add_argument("--nature", help="已知大自然音效的文件名（参照）")
    ap.add_argument("--only", action="append", default=[],
                    help="只测这些文件名（可重复）；不给就测目录里全部")
    a = ap.parse_args()

    d = os.path.abspath(a.dir)
    work = os.path.join(d, "_过程文件")
    os.makedirs(work, exist_ok=True)
    files = sorted(f for f in os.listdir(d)
                   if f.lower().endswith(AUDIO_EXTS) and not f.startswith("_")
                   and os.path.isfile(os.path.join(d, f)))
    if a.only:
        files = [f for f in files if f in a.only]

    rows = []
    for f in files:
        r = probe(os.path.join(d, f), a.secs, a.start, work)
        if not r:
            print(f"  ⚠️ {f}：取不到特征")
            continue
        tag = ""
        if f == a.piano:
            tag = "【参照·钢琴】"
        elif f == a.nature:
            tag = "【参照·大自然】"
        rows.append((f, r, tag))
        print(f"  {tag or '          '} {f}")
    print("=" * 100)
    print(f"取 {a.secs:.0f}s（从第 {a.start:.0f} 秒起）｜逐帧统计")
    print("=" * 100)
    print(f"  {'文件':<46}{'质心Hz':>9}{'平坦度':>9}{'通量中位':>10}"
          f"{'通量P90':>10}{'起音对比度':>11}")
    for f, r, tag in rows:
        nm = (f[:44] + "..") if len(f) > 46 else f
        print(f"  {nm:<46}{r['centroid']:>9.0f}{r['flatness']:>9.4f}"
              f"{r['flux_med']:>10.4f}{r['flux_p90']:>10.4f}{r['flux_ratio']:>11.2f}"
              f"  {tag}")
    print("\n判读：**起音对比度**高＝一颗颗音符（钢琴类）；低＝连续氛围（大自然/衬底）。"
          "\n      **平坦度**高＝噪声样（水/风/沙沙）；低＝谐波（乐器/咏唱）。"
          "\n      ⛔ 这只是**相对推测**，最终以人耳为准。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
