# -*- coding: utf-8 -*-
r"""
从一首 BGM 里挑出「电平最平稳的一段」，并做成**无缝循环文件**。

为什么要有它（2026-10-01 用户反馈）：
  「中间有几个地方背景音会突然变强」「不确定是不是 MP3 本身正好赶上音量提升」
  → 直接把整首曲子垫底，曲子自己的起落会带进成片。
  用户要的不是"表现力"，是"别让口播太干" → 所以**取一段平的、循环用**。

做法：
  1. 逐秒量 RMS（astats + ametadata），得到电平曲线；
  2. 滑窗找 **max−min 最小**的一段（即最平的一段），并按"不要太轻"过滤；
  3. 输出时把段尾与段首**交叉淡化**接起来（crossfade loop）→ 循环点不"咔"、无台阶。

用法：
  python bgm_pick_even_segment.py "BGM/曲子.mp3" --length 60                 # 只看分析
  python bgm_pick_even_segment.py "BGM/曲子.mp3" --length 60 --out 循环.wav   # 顺便出循环文件
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

FF = os.path.join(os.path.expanduser("~"),
                  ".workbuddy", "binaries", "ffmpeg", "bin", "ffmpeg.exe")
if not os.path.isfile(FF):
    FF = "ffmpeg"


def per_second_rms(path: str, workdir: str, win: int = 1.0):
    """逐秒 RMS（dB）。返回 [(t_center, rms), ...]"""
    os.makedirs(workdir, exist_ok=True)
    txt = os.path.join(workdir, "_rms.txt")
    if os.path.exists(txt):
        os.remove(txt)
    p = subprocess.run(
        [FF, "-hide_banner", "-y", "-i", os.path.abspath(path),
         "-af", (f"asetnsamples=n={int(48000*win)},"
                 "astats=metadata=1:reset=1,"
                 f"ametadata=print:key=lavfi.astats.Overall.RMS_level:file={os.path.basename(txt)}"),
         "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=workdir)
    if not os.path.isfile(txt):
        print((p.stderr or "")[-800:])
        raise SystemExit("⛔ 取电平曲线失败")
    vals = []
    for ln in open(txt, encoding="utf-8", errors="replace"):
        m = re.search(r"RMS_level=(-?[\d.]+|-?inf)", ln)
        if m:
            v = m.group(1)
            vals.append(-120.0 if "inf" in v else float(v))
    return [(i * win + win / 2.0, v) for i, v in enumerate(vals)]


def flattest(vals, length_s: float, win: float, min_drop_db: float = 25.0):
    """滑窗找 max−min 最小的段。返回候选列表 [(range, start, mean, mn, mx), ...]"""
    n = int(round(length_s / win))
    if n < 2 or n > len(vals):
        return []
    out = []
    for i in range(0, len(vals) - n + 1):
        seg = [v for _, v in vals[i:i + n]]
        seg = [v for v in seg if v > -110]          # 忽略纯静音窗
        if len(seg) < n * 0.9:
            continue
        mn, mx = min(seg), max(seg)
        mean = sum(seg) / len(seg)
        if mean < -60.0:                            # 太轻（前奏/尾静音）不要
            continue
        out.append((mx - mn, i * win, mean, mn, mx))
    out.sort(key=lambda x: x[0])
    return out


def make_loop(src: str, start: float, length: float, xfade: float, out: str):
    r"""
    取 region = [start, start+length)，做成**长 length 的无缝循环**。

    正确接法（⛔ 一开始写反过，务必照这个）：
        out = region[X : L]  ++  ( 淡出(region[L-X : L]) ＋ 淡入(region[0 : X]) )
    判据：out 的第一个样点 = region[X]，交叉段最后一个样点也 ≈ region[X]
        → **循环回头时是"同一个点接同一个点"，天然无缝**。
    ⛔ 常见错法：写成 (淡出(region[0:X]) ＋ 淡入(region[L:L+X])) ++ region[X:L]
        —— 那个的循环缝是 region[L] → region[0]，**对不上，会"咔"**。
    """
    L, X = length, xfade
    fc = (
        f"[0:a]atrim=start={start:.3f}:end={start + L:.3f},asetpts=N/SR/TB,"
        f"asplit=3[r1][r2][r3];"
        f"[r1]atrim=start={L - X:.3f}:end={L:.3f},asetpts=N/SR/TB,"
        f"afade=t=out:st=0:d={X:.3f}[tail];"
        f"[r2]atrim=start=0:end={X:.3f},asetpts=N/SR/TB,"
        f"afade=t=in:st=0:d={X:.3f}[head];"
        f"[tail][head]amix=inputs=2:duration=first:normalize=0[xf];"
        f"[r3]atrim=start={X:.3f}:end={L:.3f},asetpts=N/SR/TB[body];"
        f"[body][xf]concat=n=2:v=0:a=1[out]"
    )
    p = subprocess.run(
        [FF, "-hide_banner", "-y", "-i", os.path.abspath(src),
         "-filter_complex", fc, "-map", "[out]",
         "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", os.path.abspath(out)],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        print((p.stderr or "")[-1200:])
        raise SystemExit("⛔ 生成循环文件失败")
    return out


def seam_check(path: str) -> tuple[float, float]:
    r"""
    核验循环缝：把文件的**最后一个样点 → 第一个样点**当作一次循环回头，
    比较这个跳变与文件内部相邻样点跳变的常态水平。

    ⛔ 只看"有没有咔"不能靠耳朵——用数字：seam ≤ 内部 99.9 分位 ×3 就算无缝。
    ⚠️ 90 秒 48kHz 立体声 = 864 万个样点，**必须向量化**：
       早期版本把每个样点切成 list，一个片段要跑十几秒且吃几百 MB 内存。
       → 有 numpy 用 numpy；没有就**抽样**算分位（缝那一点仍然精确算）。
    """
    import array
    import wave

    with wave.open(path, "rb") as w:
        ch, sw, n = w.getnchannels(), w.getsampwidth(), w.getnframes()
        raw = w.readframes(n)
    if sw != 2:
        return float("nan"), float("nan")
    try:
        import numpy as np
        a = np.frombuffer(raw, dtype="<i2").reshape(-1, ch).astype(np.int32)
        if a.shape[0] < 1000:
            return float("nan"), float("nan")
        seam = float(np.abs(a[-1] - a[0]).max())
        d = np.abs(np.diff(a, axis=0)).max(axis=1)
        return seam, float(np.percentile(d, 99.9))
    except ImportError:
        a = array.array("h")
        a.frombytes(raw)
        frames = len(a) // ch
        if frames < 1000:
            return float("nan"), float("nan")

        def jdiff(i):                       # 第 i 帧与第 i-1 帧的样点最大跳变（全分辨率）
            return max(abs(a[i * ch + c] - a[(i - 1) * ch + c]) for c in range(ch))

        seam = max(abs(a[(frames - 1) * ch + c] - a[c]) for c in range(ch))
        step = max(1, frames // 200000)     # 抽样**索引**，但仍在全分辨率上算差值
        inner = sorted(jdiff(i) for i in range(step, frames, step))
        p999 = inner[min(len(inner) - 1, int(len(inner) * 0.999))]
        return float(seam), float(p999)


def main() -> int:
    ap = argparse.ArgumentParser(description="挑一段电平最平稳的 BGM 并做无缝循环")
    ap.add_argument("bgm")
    ap.add_argument("--length", type=float, default=60.0, help="循环段长度（秒）")
    ap.add_argument("--xfade", type=float, default=2.5, help="循环点交叉淡化秒数")
    ap.add_argument("--win", type=float, default=1.0, help="取样窗口秒数")
    ap.add_argument("--top", type=int, default=6)
    ap.add_argument("--out", help="输出循环文件（wav）；不给则只分析")
    a = ap.parse_args()

    work = os.path.join(os.path.dirname(os.path.abspath(a.out or a.bgm)), "_过程文件")
    vals = per_second_rms(a.bgm, work, a.win)
    total = len(vals) * a.win
    print("=" * 68)
    print(f"电平分析：{os.path.basename(a.bgm)}")
    print("=" * 68)
    print(f"  窗口数 {len(vals)}（{a.win}s/窗，约 {total:.0f}s）")
    live = [v for _, v in vals if v > -110]
    if live:
        print(f"  有声音的窗：{len(live)}  最轻 {min(live):.1f} dB  最响 {max(live):.1f} dB"
              f"  极差 {max(live)-min(live):.1f} dB")
    # 掐个头尾看曲线
    print("\n  电平曲线（每 10s 一个点，▁▂▃▄▅▆▇█ 越高越响）：")
    blocks = []
    step = max(1, int(10 / a.win))
    for i in range(0, len(vals), step):
        seg = [v for _, v in vals[i:i + step]]
        blocks.append(sum(seg) / len(seg) if seg else -120)
    lo, hi = min(blocks), max(blocks)
    lv = "▁▂▃▄▅▆▇█"
    line = "".join(lv[min(7, int((b - lo) / max(1e-6, hi - lo) * 7.99))] for b in blocks)
    for i in range(0, len(line), 60):
        print(f"    {i*10:>4}s {line[i:i+60]}")

    ranked = flattest(vals, a.length, a.win)
    if not ranked:
        raise SystemExit(f"⛔ 找不到 {a.length}s 长的平稳段（曲子可能太短）")
    print(f"\n  最平稳的 {a.length:.0f}s 段（按 极差 升序）：")
    print(f"    {'起(s)':>8} {'极差':>7} {'均值':>7} {'最轻':>7} {'最响':>7}")
    for rng, st, mean, mn, mx in ranked[:a.top]:
        print(f"    {st:>8.1f} {rng:>6.1f} {mean:>7.1f} {mn:>7.1f} {mx:>7.1f}")
    rng, st, mean, mn, mx = ranked[0]
    print(f"\n  → 选定：{st:.1f}s 起，{a.length:.0f}s（极差 {rng:.1f} dB）")

    if a.out:
        make_loop(a.bgm, st, a.length, a.xfade, a.out)
        print(f"  ✅ 循环文件：{a.out}")
        print(f"     （{a.length:.0f}s，尾部 {a.xfade:.1f}s 与开头交叉淡化，循环点无缝）")
        seam, p999 = seam_check(a.out)
        if seam == seam:                      # 不是 NaN
            ok = seam <= p999 * 3
            print(f"     循环缝核验：缝上跳变 {seam:.0f} / 内部 99.9 分位 {p999:.0f}"
                  f"  → {'✅ 无缝' if ok else '⚠️ 可能有点击声'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
