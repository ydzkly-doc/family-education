# -*- coding: utf-8 -*-
r"""
系列 BGM 核对 —— 一张表看清「每条成片的 BGM 配置与暴露程度」。

为什么要它（2026-10-01）：
  压低（ducking）的实际"暴露量"取决于**人声段的分布**，而这是每条都不同的：
  001 条有 21 段、03 条只有 5 段 → 同样是 `压低 8dB`，音乐"露出来"的机会差很多。
  靠肉眼看 MD 看不出来，得数。

用法：
  python 工具脚本/video_bgm_series_check.py <系列目录> [--glob "0*"] [--offset 2.0]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SKILL = os.path.join(os.path.expanduser("~"), ".workbuddy", "skills",
                     "ffmpeg-vertical-video-pipeline", "scripts")
sys.path.insert(0, SKILL)
import video_bgm as vb          # noqa: E402

FF = os.path.join(os.path.expanduser("~"),
                  ".workbuddy", "binaries", "ffmpeg", "bin", "ffmpeg.exe")


def duration(p: str) -> float:
    r = subprocess.run([FF, "-hide_banner", "-i", os.path.abspath(p)],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    m = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", r.stderr or "")
    if not m:
        return 0.0
    h, mi, s = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(s)


def band(path: str, start: float, dur: float = 0.8,
         hp: int = 120, lp: int = 600) -> float:
    """同时间点、带通后的 mean_volume（dB）——等位对照用（口径同技能 selftest ⑦）"""
    p = subprocess.run(
        [FF, "-hide_banner", "-ss", f"{start}", "-t", f"{dur}",
         "-i", os.path.abspath(path),
         "-af", f"highpass=f={hp},lowpass=f={lp},volumedetect", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.search(r"mean_volume:\s*(-?[\d.]+)", p.stderr or "")
    return float(m.group(1)) if m else -120.0


def per_sec(path: str, hp: int = 120, lp: int = 600):
    """逐秒带通 RMS（dB）——一次 ffmpeg 出全部窗口"""
    d = os.path.dirname(os.path.abspath(path)) or "."
    txt = "_serms.txt"
    fp = os.path.join(d, txt)
    if os.path.exists(fp):
        os.remove(fp)
    p = subprocess.run(
        [FF, "-hide_banner", "-y", "-i", os.path.abspath(path),
         "-af", (f"highpass=f={hp},lowpass=f={lp},asetnsamples=n=48000,"
                 "astats=metadata=1:reset=1,"
                 f"ametadata=print:key=lavfi.astats.Overall.RMS_level:file={txt}"),
         "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=d)
    out = []
    if os.path.isfile(fp):
        for ln in open(fp, encoding="utf-8", errors="replace"):
            m = re.search(r"RMS_level=(-?[\d.]+|-?inf)", ln)
            if m:
                v = m.group(1)
                out.append(-120.0 if "inf" in v else float(v))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="系列 BGM 核对")
    ap.add_argument("series_dir")
    ap.add_argument("--glob", default="0*", help="条目目录匹配（默认 0*）")
    ap.add_argument("--offset", type=float, default=2.0,
                    help="timings 相对成片的时间码偏移（前置封面卡时长）")
    ap.add_argument("--gain", type=float, default=-12.0)
    ap.add_argument("--duck", type=float, default=8.0)
    ap.add_argument("--bgm", default=os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "_资产", "bgm", "传递的温柔_等电平循环90s.wav"),
        help="曲目文件（只用来让 vb.plan 解析；不读它的内容）")
    a = ap.parse_args()

    # ⛔ 压低区间一律**问 plan() 要**，不在这里自己算一遍（否则两处口径迟早不同步）
    cfg = {"file": a.bgm, "placement": "全程", "gain": a.gain,
           "duck": a.duck, "duck_ramp": 0.35}

    rows = []
    for name in sorted(os.listdir(a.series_dir)):
        d = os.path.join(a.series_dir, name)
        if not os.path.isdir(d) or not re.match(a.glob, name):
            continue
        out = os.path.join(d, "_成品")
        if not os.path.isdir(out):
            continue
        mp4 = next((os.path.join(out, f) for f in sorted(os.listdir(out))
                    if re.match(r"成片_\d+\.mp4$", f)), None)
        bgm = os.path.join(out, "成片_%s_带BGM.mp4" %
                           (re.search(r"成片_(\d+)", os.path.basename(mp4)).group(1)
                            if mp4 else "?"))
        tj = os.path.join(out, "_过程文件", "timings.json")
        if not mp4:
            rows.append((name, "—", "无成片", "", "", "", "", "—", ""))
            continue
        D = duration(mp4)
        n_lines = n_span = 0
        duck_pct = 0.0
        first = last = 0.0
        extra = ""
        if os.path.isfile(tj):
            L = json.load(open(tj, encoding="utf-8"))["lines"]
            seg = [{"start": float(x["start"]) + a.offset,
                    "end": float(x["end"]) + a.offset,
                    "text": x.get("text", "")} for x in L]
            plan = vb.plan(dict(cfg), seg, D, [])
            sp = plan.get("duck_spans") or []
            n_lines = len(L)
            n_span = len(sp)
            duck_pct = sum(e - s for s, e in sp) / D * 100 if D else 0.0
            first, last = seg[0]["start"], seg[-1]["end"]
            # ⭐ 音乐"露不露得出来"，要看**真正安静**的地方，而不是"时间码空当"
            #    （时间码的句子之间，真人可能只是没被识别到，并不是安静）
            if os.path.isfile(bgm):
                sers = per_sec(mp4)
                # ⛔ 先剔除数字静音（封面卡那种 -120dB），否则"最安静的 5 秒"全落在它上面，
                #    测出来什么也说明不了（实测踩过）
                cand = [i for i in range(len(sers)) if sers[i] > -110]
                idx = sorted(cand, key=lambda i: sers[i])[:5]
                ds = [band(bgm, i + 0.5, 0.5) - band(mp4, i + 0.5, 0.5)
                      for i in idx]
                quiet = (f"原片最安静的 5 秒（剔静音）：Δ "
                         + "/".join(f"{x:+.1f}" for x in ds) + " dB"
                         + f"（最安静那秒原片 {sers[idx[0]]:.0f} dB）") if ds else ""
                talk = band(bgm, (sp[0][0] + sp[0][1]) / 2.0) \
                    - band(mp4, (sp[0][0] + sp[0][1]) / 2.0) if sp else 0.0
                extra = f"{quiet} ｜ 说话处 Δ{talk:+.1f} dB"
        rows.append((name,
                     f"{D:.1f}s",
                     f"{n_lines} 句 / {n_span} 段",
                     f"{duck_pct:.0f}%",
                     f"{first:.1f}~{last:.1f}",
                     f"{a.gain:.0f} dB",
                     f"{a.gain - a.duck:.0f} dB",
                     "✅" if os.path.isfile(bgm) else "—",
                     f"{os.path.getsize(bgm)/1e6:.0f} MB" if os.path.isfile(bgm) else "",
                     extra))

    print("=" * 92)
    print(f"系列 BGM 核对：{os.path.basename(os.path.normpath(a.series_dir))}"
          f"（时间码偏移 +{a.offset:.1f}s）")
    print("=" * 92)
    hdr = ("条目", "片长", "人声", "压低占比", "人声范围", "开口处", "说话处",
           "带BGM成片", "体积")
    print("  " + "  ".join(f"{h:<12}" for h in hdr))
    for r in rows:
        print("  " + "  ".join(f"{c:<12}" for c in r[:9]))
        if len(r) > 9 and r[9]:
            print(f"      ↳ {r[9]}")
    print("\n说明：「压低占比」＝人声段累计时长 ÷ 片长，即音乐被压下去的时间比例；"
          "\n      占满 → 音乐几乎一直处于「说话处」的电平，「开口处」那一档很少露出来。"
          "\n      「Δ」＝ 带BGM 与原片在同时间点的带通(120-600Hz)电平差；"
          "开口处应明显 >0（垫进去了），说话处应很小（没糊住人声）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
