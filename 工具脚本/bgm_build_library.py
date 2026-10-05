# -*- coding: utf-8 -*-
r"""
批量建 BGM 曲库片段 —— 从一批曲子里，每首挑 **1~n 段最平的**，做成**无缝循环**，统一响度。

为什么要有它（2026-10-01 第 2 次）：
  用户一次给了 6 首"大自然解压放松"系列（5~15 分钟）当曲库素材。
  一首一首手挑 + 手工接循环，会重复十几次同一套动作，而且**容易挑到有起落的段**。
  → 批量跑：逐秒量电平 → 滑窗找最平的几段 → 交叉淡化接循环 → **响度拉齐** → 出候选表。

⭐ **响度拉齐是关键**：管道里的 `音量` 是"相对口播的 dB"，若各首曲子响度不一，
  换一首就得重调一次音量。→ 所有片段统一归一到一个目标响度（默认 **−18.3 LUFS**，
  即本项目现用曲子的实测值），**现有 `--gain -12` 对每段都成立**。

⛔ 只产出**候选**；登记进 `_资产/bgm/曲库.md` 由人确认后做。

用法：
  python 工具脚本/bgm_build_library.py \
      --src "BGM" --out "BGM/_曲库候选" \
      --length 90 --per-file 2 --xfade 2.5 \
      --exclude "传递的温柔*" --exclude "_*"
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from bgm_pick_even_segment import (   # noqa: E402  直接复用，别再写一遍
    FF, make_loop, per_second_rms, seam_check)

AUDIO_EXTS = (".mp3", ".m4a", ".aac", ".wav", ".flac", ".ogg", ".opus", ".wma")

# 文件名里反复出现的系列名，做短名时去掉（不影响匹配，纯粹为好读）
NOISE_SUFFIX = ("大自然解压放松音乐", "解压放松音乐")

# ⛔ 太高饱和/太"亮"的曲子不适合垫底，但这是内容判断，不在这里自动过滤，只报告


def slug(stem: str) -> str:
    s = stem
    for w in NOISE_SUFFIX:
        s = s.replace(w, "")
    for ch in "【】[]（）()":
        s = s.replace(ch, "")            # ⛔ 只 strip 首尾会留下"【A】B"中间那个"】"
    s = s.strip(" 　-_·，,。.、！!？?")
    s = re.sub(r"\s+", "", s)
    return s or "未命名"


def probe_loudness(path: str) -> tuple[float, float]:
    """返回 (integrated LUFS, true peak dBTP)"""
    p = subprocess.run(
        [FF, "-hide_banner", "-i", os.path.abspath(path), "-af",
         "loudnorm=print_format=summary", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    t = p.stderr or ""
    i = re.search(r"Input Integrated:\s*(-?[\d.]+)", t)
    tp = re.search(r"Input True Peak:\s*(-?[\d.]+)", t)
    return (float(i.group(1)) if i else float("nan"),
            float(tp.group(1)) if tp else float("nan"))


def peak_db(path: str) -> float:
    p = subprocess.run(
        [FF, "-hide_banner", "-i", os.path.abspath(path),
         "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.search(r"max_volume:\s*(-?[\d.]+)", p.stderr or "")
    return float(m.group(1)) if m else 0.0


def apply_gain(src: str, dst: str, gain_db: float) -> bool:
    p = subprocess.run(
        [FF, "-hide_banner", "-y", "-i", os.path.abspath(src),
         "-af", f"volume={gain_db:.2f}dB",
         "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", os.path.abspath(dst)],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode == 0 and os.path.isfile(dst)


def make_preview(src: str, dst: str) -> bool:
    """连播两遍的小体积 MP3 —— 听接缝用（90s 一段，第二遍接缝就露出来了）"""
    p = subprocess.run(
        [FF, "-hide_banner", "-y", "-stream_loop", "1", "-i", os.path.abspath(src),
         "-c:a", "libmp3lame", "-b:a", "192k", os.path.abspath(dst)],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode == 0 and os.path.isfile(dst)


def pick_segments(vals: list[float], length: float, win: float, n_max: int):
    """
    逐秒电平 → 挑 n_max 段**互不重叠**、**段内极差最小**的窗口。
    过滤：① 段内含纯静音（≤ −110）→ 弃；② 段均值比全曲中位低 6dB 以上 → 太轻，弃。
    """
    n = int(round(length / win))
    if n < 2 or n > len(vals):
        return []
    live = [v for v in vals if v > -110]
    med = sorted(live)[len(live) // 2] if live else -60
    floor = max(med - 6.0, -80.0)
    cands = []
    for i in range(0, len(vals) - n + 1):
        seg = vals[i:i + n]
        if any(v <= -110 for v in seg):
            continue
        mean = sum(seg) / len(seg)
        if mean < floor:
            continue
        cands.append({"start": i * win, "range": max(seg) - min(seg),
                      "mean": mean, "min": min(seg), "max": max(seg),
                      "spikes": sum(1 for v in seg if v > mean + 6.0)})
    cands.sort(key=lambda c: (c["range"], -c["mean"]))
    picked = []
    for c in cands:
        if all(abs(c["start"] - p["start"]) >= length * 1.2 for p in picked):
            picked.append(c)
        if len(picked) >= n_max:
            break
    return picked


def main() -> int:
    ap = argparse.ArgumentParser(description="批量建 BGM 曲库片段")
    ap.add_argument("--src", required=True, help="源目录（扫 *.mp3 等）")
    ap.add_argument("--out", required=True, help="输出目录（候选片段 + 试听 + 清单）")
    ap.add_argument("--lengths", default="90,45",
                    help="要出哪几种长度的候选（逗号分隔，秒）。"
                         "⭐ 段的**长度与「平不平」是矛盾的**：越短越平、但循环次数越多，"
                         "所以一次给两种长度，让人**听着挑**")
    ap.add_argument("--per-length", type=int, default=1, dest="per_length",
                    help="每种长度最多出几段（1~n）")
    ap.add_argument("--xfade", type=float, default=2.5, help="循环点交叉淡化秒数")
    ap.add_argument("--win", type=float, default=1.0)
    ap.add_argument("--target-lufs", type=float, default=-18.3,
                    dest="target_lufs", help="统一目标响度（默认＝现用曲子的实测值）")
    ap.add_argument("--peak-ceiling", type=float, default=-3.0, dest="peak_ceiling",
                    help="峰值上限 dBFS（提响度时不许越线）")
    ap.add_argument("--exclude", action="append", default=[],
                    help="文件名通配排除，可重复")
    a = ap.parse_args()

    src_dir = os.path.abspath(a.src)
    out_dir = os.path.abspath(a.out)
    loops_dir = os.path.join(out_dir, "循环片段")
    prev_dir = os.path.join(out_dir, "试听")
    work = os.path.join(out_dir, "_过程文件")
    for d in (loops_dir, prev_dir, work):
        os.makedirs(d, exist_ok=True)

    import fnmatch
    files = sorted(f for f in os.listdir(src_dir)
                   if f.lower().endswith(AUDIO_EXTS)
                   and not f.startswith("_")
                   and os.path.isfile(os.path.join(src_dir, f))
                   and not any(fnmatch.fnmatch(f, p) for p in a.exclude))

    lengths = [float(x) for x in str(a.lengths).replace("，", ",").split(",") if x.strip()]
    print("=" * 96)
    print(f"批量建库：{src_dir}")
    print(f"  曲子 {len(files)} 首｜长度 {('、'.join(f'{L:.0f}s' for L in lengths))}"
          f"（每种最多 {a.per_length} 段）"
          f"｜统一响度 {a.target_lufs:.1f} LUFS｜峰值上限 {a.peak_ceiling:.1f} dBFS")
    print("=" * 96)

    rows = []
    for fi, f in enumerate(files, 1):
        path = os.path.join(src_dir, f)
        base = slug(os.path.splitext(f)[0])
        print(f"\n[{fi}/{len(files)}] {f}")
        # per_second_rms 返回 [(时间, RMS), ...]，这里只要电平序列
        vals = [v for _, v in per_second_rms(path, work, a.win)]
        live = [v for v in vals if v > -110]
        if live:
            print(f"    逐秒电平：{len(vals)} 窗｜最轻 {min(live):.1f}｜最响 {max(live):.1f}"
                  f"｜极差 {max(live)-min(live):.1f} dB")
        for L in lengths:
            picks = pick_segments(vals, L, a.win, a.per_length)
            if not picks:
                print(f"    L={L:.0f}s ⛔ 找不到可用的平段 → 跳过")
                rows.append((base, "—", f"{L:.0f}s", "—", "—", "—", "—", "跳过"))
                continue
            for k, c in enumerate(picks, 1):
                tag = chr(ord("A") + k - 1)
                name = f"{base}_循环{L:.0f}s_{tag}"
                raw = os.path.join(work, f"_raw_{base}_{L:.0f}_{tag}.wav")
                out = os.path.join(loops_dir, name + ".wav")
                make_loop(path, c["start"], L, a.xfade, raw)
                lufs, _tp = probe_loudness(raw)
                pk = peak_db(raw)
                gain = a.target_lufs - lufs
                capped = ""
                if pk + gain > a.peak_ceiling:
                    gain = a.peak_ceiling - pk
                    capped = "（受峰值上限限制）"
                apply_gain(raw, out, gain)
                f_lufs, f_tp = probe_loudness(out)
                seam, p999 = seam_check(out)
                ok_seam = seam <= p999 * 3
                make_preview(out, os.path.join(prev_dir, name + "_试听.mp3"))
                os.remove(raw)
                print(f"    L={L:>3.0f}s {tag}: {c['start']:>6.1f}s 起｜"
                      f"极差 {c['range']:>5.1f} dB｜均值 {c['mean']:>6.1f}｜"
                      f"尖峰 {c['spikes']:>2} 秒｜增益 {gain:>+6.1f} dB{capped}｜"
                      f"成品 {f_lufs:.1f} LUFS / {f_tp:.1f} dBTP｜"
                      f"缝 {seam:.0f} vs {p999:.0f} {'✅' if ok_seam else '⚠️'}")
                rows.append((base, tag, f"{L:.0f}s", f"{c['start']:.0f}s",
                             f"{c['range']:.1f}", f"{c['spikes']}", f"{gain:+.1f}",
                             f"{f_lufs:.1f} / {f_tp:.1f}",
                             "✅" if ok_seam else "⚠️"))
    return write_report(a, lengths, rows, loops_dir, prev_dir, out_dir)


def write_report(a, lengths, rows, loops_dir, prev_dir, out_dir) -> int:
    lines = ["# BGM 曲库候选（待确认）", "",
             f"> 由 `工具脚本/bgm_build_library.py` 生成 · 源目录 `{a.src}`",
             f"> 长度 {('、'.join(f'{L:.0f}s' for L in lengths))}"
             f"· 循环点交叉淡化 {a.xfade:.1f}s · "
             f"响度统一归一 **{a.target_lufs:.1f} LUFS** · 峰值 ≤ {a.peak_ceiling:.1f} dBFS",
             "> ⛔ **这些只是候选**，确认后才登记进 `_资产/bgm/曲库.md`。", "",
             "## 候选清单", "",
             "| 原曲 | 段 | 长度 | 起点 | 段内极差(dB) | 尖峰秒数 | 增益 | 成品 LUFS/dBTP | 循环缝 |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append("| " + " | ".join(str(x) for x in r) + " |")
    lines += ["",
              "**怎么读**：",
              "- **段内极差**越小＝这一段越平（越不容易「忽大忽小」）。同长度的候选先比这个。",
              "- **长度越长越不平**（曲子自己的起落跑不掉）：所以同时给了 90s 与 45s 两种，"
              "**听着挑**——90s 循环次数少、45s 更平。",
              "- **尖峰秒数**：段内比该段均值高 6dB 以上的秒数（鸟叫、水滴之类）。"
              "这种偶发响声循环起来会被记住，尽量挑 0 的。",
              "- **增益**是相对原曲加的，已经算好使成品落在统一响度——"
              "所以**同一套音量参数对每段都成立**。",
              "- **循环缝**：`缝跳变 ≤ 内部 99.9 分位 ×3` 判为无缝（`✅`）。",
              "",
              "## 文件放哪", "",
              f"- `循环片段/` —— **无缝循环 WAV**（确认后把选中的登记进曲库）",
              f"- `试听/` —— **连播两遍的试听 MP3**（小，先听这个；**第二遍的接缝能听出来**）",
              "",
              "## 下一步（等你确认）", "",
              "1. 听试听，挑出可用的段（可以每首只留一段，也可以留多段）",
              "2. 确认后我再：把选中的 WAV 放进 `_资产/bgm/`、写进 `曲库.md`（风格/情绪/适用）",
              ""]
    p = os.path.join(out_dir, "候选清单.md")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print("\n" + "=" * 96)
    print(f"✅ 候选清单：{p}")
    print(f"   循环片段 {len(os.listdir(loops_dir))} 个｜试听 {len(os.listdir(prev_dir))} 个")
    print("=" * 96)
    return 0


if __name__ == "__main__":
    sys.exit(main())
