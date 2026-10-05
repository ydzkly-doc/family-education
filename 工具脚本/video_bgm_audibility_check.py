# -*- coding: utf-8 -*-
r"""核验「BGM 到底垫进去了没有」—— 同时间点、带通后的等位对照。

判据（与技能 video_bgm.selftest ⑦ 同一口径）：
  · 人声段：混音后应与纯口播**几乎一致**（BGM 被压低 → 漏不进来）
  · 静音段（句间停顿）：混音后应**明显高于**纯口播（BGM 在这里露出来）
⛔ 只测带通（highpass/lowpass）—— 否则口播在阻带的泄漏会污染读数。
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

FF = os.path.expanduser("~/.workbuddy/binaries/ffmpeg/bin/ffmpeg.exe")


def band(path: str, start: float, dur: float = 0.8,
         hp: int = 120, lp: int = 600) -> float:
    p = subprocess.run(
        [FF, "-hide_banner", "-ss", f"{start}", "-t", f"{dur}", "-i", path,
         "-af", f"highpass=f={hp},lowpass=f={lp},volumedetect", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.search(r"mean_volume:\s*(-?[\d.]+)", p.stderr or "")
    return float(m.group(1)) if m else -120.0


def band_mean(path: str, start: float, dur: float,
              hp: int, lp: int) -> float:
    """带通后的 mean_volume（dB）"""
    return band(path, start, dur, hp, lp)


def per_sec_band(path: str, hp: int, lp: int, win: float = 1.0):
    """
    一次 ffmpeg 跑完：带通 → 按 win 秒切窗 → 每窗 RMS（dB）。
    ⛔ 不要"每个时间点起一次 ffmpeg"——280 个点会跑到几分钟（实测被超时打断）。
    """
    d = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(d, exist_ok=True)
    txt = "_bandrms.txt"
    fp = os.path.join(d, txt)
    if os.path.exists(fp):
        os.remove(fp)
    p = subprocess.run(
        [FF, "-hide_banner", "-y", "-i", os.path.abspath(path),
         "-af", (f"highpass=f={hp},lowpass=f={lp},"
                 f"asetnsamples=n={int(48000*win)},"
                 "astats=metadata=1:reset=1,"
                 f"ametadata=print:key=lavfi.astats.Overall.RMS_level:file={txt}"),
         "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=d)
    if not os.path.isfile(fp):
        return []
    vals = []
    for ln in open(fp, encoding="utf-8", errors="replace"):
        m = re.search(r"RMS_level=(-?[\d.]+|-?inf)", ln)
        if m:
            v = m.group(1)
            vals.append(-120.0 if "inf" in v else float(v))
    return vals


def music_profile(orig: str, mix: str, step: float = 1.0, dur: float = 1.0,
                  hp: int = 120, lp: int = 600, lo: float = 0.05,
                  hi: float = 12.0):
    r"""
    估算**「垫进去的音乐」逐秒电平**（一次 ffmpeg 出全部窗口，快）。

    原理：混音后 = 原声 ⊕ 音乐（功率相加，不是 dB 相加）
        Δ(dB) = 10·lg(1 + P_m/P_o)  →  P_m = P_o · (10^(Δ/10) − 1)
    ⛔ Δ 落在 [lo, hi] 之外时不可信（几乎没垫上 / 差值小到读不出），跳过。
       所以看的是**分布**，不是逐点绝对值。
    """
    import math
    a = per_sec_band(orig, hp, lp, dur)
    b = per_sec_band(mix, hp, lp, dur)
    out = []
    for i, (po, pm) in enumerate(zip(a, b)):
        d = pm - po
        if lo < d < hi and po > -110:
            p_o = 10 ** (po / 10.0)
            p_m = p_o * (10 ** (d / 10.0) - 1)
            out.append((i * step, 10 * math.log10(max(p_m, 1e-12))))
    return out


def duration_of(path: str) -> float:
    p = subprocess.run([FF, "-hide_banner", "-i", path],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", p.stderr or "")
    if not m:
        return 0.0
    h, mi, s = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(s)


def main():
    variants = [a for a in sys.argv[1:] if not a.startswith("--")]
    points = []
    step = 1.0
    do_profile = False
    for a in sys.argv:
        if a.startswith("--at="):
            for x in a[5:].split(","):
                t, tag = x.split(":", 1)
                points.append((float(t), tag))
        elif a.startswith("--step="):
            step = float(a[7:])
            do_profile = True
        elif a == "--profile":
            do_profile = True
    if not variants:
        sys.exit("用法：video_bgm_audibility_check.py <原片> <混音后> [...] "
                 "[--at=12.5:说明,...] [--profile] [--step=1]")
    orig = variants[0]
    if do_profile:
        print("=" * 74)
        print("「垫进去的音乐」逐秒电平估算（带通 120-600Hz，功率相减法）")
        print("=" * 74)
        for v in variants[1:]:
            prof = music_profile(orig, v, step=step)
            if not prof:
                print(f"  {os.path.basename(v)}：样本不足，读不出")
                continue
            vals = [x for _, x in prof]
            vals_s = sorted(vals)
            n = len(vals)
            p10, p90 = vals_s[int(n * 0.1)], vals_s[int(n * 0.9)]
            print(f"\n  {os.path.basename(v)}")
            print(f"    样本 {n} 个｜中位 {vals_s[n//2]:.1f} dB｜"
                  f"P10 {p10:.1f}｜P90 {p90:.1f}｜"
                  f"**P10~P90 跨度 {p90-p10:.1f} dB**（越小越平）")
            bars = ""
            for t, x in prof[::max(1, int(len(prof) / 46))]:
                idx = min(7, max(0, int((x - (p10 - 3)) / max(1e-6, (p90 + 3) - (p10 - 3)) * 7.99)))
                bars += "▁▂▃▄▅▆▇█"[idx]
            print(f"    电平走势：{bars}")
        return
    if not points:
        points = [(3.0, "封面卡（BGM应最响）"), (30.0, "人声段"),
                  (250.0, "人声段2")]
    print(f"{'时间':>7} {'场景':<16} " +
          " ".join(f"{os.path.basename(v)[-18:]:>18}" for v in variants))
    print("-" * (26 + 19 * len(variants)))
    for t, tag in points:
        vals = [band(v, t) for v in variants]
        row = f"{t:>7.1f} {tag:<16} "
        row += " ".join(f"{x:>18.1f}" for x in vals)
        txt = "  ".join(f"{x - vals[0]:+.1f}dB" for x in vals[1:])
        print(row + "   Δ " + txt)
    print("\n（第一列 = 原成片；Δ = 相对原成片的变化，正数＝垫进了东西）")


if __name__ == "__main__":
    main()
