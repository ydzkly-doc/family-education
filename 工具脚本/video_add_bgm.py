# -*- coding: utf-8 -*-
r"""
给**已出成片**补加 BGM（试听 / 补做用）—— 视频流 `-c:v copy`，只重编码音轨。

为什么要单独写一个：
  主管道 `video_make.py` 是「素材 → 成片」全流程（重跑 ASR、重烧字幕、重编码画面），
  而「给已经定稿的成片试一下 BGM」不需要动画面 —— 用本脚本几秒钟就能听到效果，
  也不会碰坏定稿。

⛔ BGM 的全部逻辑**复用技能**（`video_bgm.plan()` / `video_bgm.build_filter()`），
   本脚本不重写一遍 —— 否则两侧迟早不同步
   （见 `_资产/BGM使用与对接说明.md` 第四节：同一格式两处各写一份，字段名撞车过）。

混音顺序与主管道一致：**先混音 → 再测 → 后 loudnorm**（SKILL 硬坑 24）。

用法：
  python 工具脚本/video_add_bgm.py \
      --video 成片_01.mp4 \
      --bgm "BGM/传递的温柔（无损钢琴曲）-安静轻音.mp3" \
      --placement 全程 --gain -24 --duck 12 \
      --timings _成品/_过程文件/timings.json --offset 2.0 \
      --out _配乐试听/成片_01_BGM全程.mp4

  # 只算不做（看 BGM 计划 / 落点区间，不出文件）
  python 工具脚本/video_add_bgm.py --video 成片_01.mp4 --bgm xx.mp3 \
      --placement 全程 --timings timings.json --offset 2.0 --probe-only
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

# ---- 技能脚本目录（权威实现所在）----
_CANDS = [
    os.environ.get("WB_SKILL_SCRIPTS"),
    os.path.join(os.path.expanduser("~"), ".workbuddy", "skills",
                 "ffmpeg-vertical-video-pipeline", "scripts"),
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "_技能", "ffmpeg-vertical-video-pipeline", "scripts"),
]
SKILL_SCRIPTS = next((c for c in _CANDS if c and os.path.isdir(c)), None)
if not SKILL_SCRIPTS:
    sys.exit("⛔ 找不到技能脚本目录（可用环境变量 WB_SKILL_SCRIPTS 指定）")
sys.path.insert(0, SKILL_SCRIPTS)

import paths as _paths          # noqa: E402
import video_audio as va        # noqa: E402
import video_bgm as vb          # noqa: E402

FFMPEG = _paths.ffmpeg_path()


def run(args, cwd=None, label=""):
    if label:
        print(f"    · {label}")
    return subprocess.run(args, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", cwd=cwd)


def probe_duration(path: str) -> float:
    p = run([FFMPEG, "-hide_banner", "-i", os.path.abspath(path)])
    m = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", p.stderr or "")
    if not m:
        raise SystemExit(f"⛔ 读不到时长：{path}")
    h, mi, s = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(s)


def load_lines(timings: str, offset: float, total: float):
    """读 timings.json 的 lines，并按 offset 平移（成片若前置过封面卡，时间码要整体后移）"""
    d = json.load(open(timings, encoding="utf-8"))
    raw = d["lines"] if isinstance(d, dict) else d
    out = []
    for ln in raw:
        s = float(ln["start"]) + offset
        e = float(ln["end"]) + offset
        if e <= 0 or s >= total:
            continue
        out.append({"text": ln.get("text", ""),
                    "start": max(0.0, s), "end": min(total, e)})
    return out


def detect_voice_bounds(video: str, noise_db: float = -32.0, min_d: float = 1.0):
    """没有时间码时的兜底：用 silencedetect 反推「人声范围」（只够头尾模式用）"""
    p = run([FFMPEG, "-hide_banner", "-i", os.path.abspath(video),
             "-af", f"silencedetect=noise={noise_db}dB:d={min_d}", "-f", "null", "-"])
    txt = p.stderr or ""
    starts = [float(x) for x in re.findall(r"silence_start:\s*(-?[\d.]+)", txt)]
    ends = [float(x) for x in re.findall(r"silence_end:\s*([\d.]+)", txt)]
    total = probe_duration(video)
    head = starts[0] if starts and starts[0] <= 0.5 else 0.0
    # 片尾静音起点 = 最后一个 silence_start（且它一直延续到片尾）
    tail = ends[-1] if ends and not (starts and starts[-1] > ends[-1]) else total
    if starts and starts[-1] > (ends[-1] if ends else -1):
        tail = starts[-1]
    return head, tail


def build_cfg(a) -> dict:
    return {
        "file": os.path.abspath(a.bgm),
        "placement": a.placement,
        "gain": a.gain,
        "duck": a.duck,
        # ⭐ 压低斜坡（秒）：>0 时压低区间做渐变，避免"背景音突然变强/变小"
        "duck_ramp": a.duck_ramp,
        "fade_in": a.fade_in,
        "fade_out": a.fade_out,
        "loop": True,
    }


def audio_chain(a, measured, duration) -> str:
    """loudnorm + 限制器 + 首尾淡入淡出（前置链已在原成片里做过，这里不再叠加）"""
    cfg = va.config_from_spec({
        "preset": "关闭",
        "loudnorm": {"enabled": True, "I": a.I, "TP": a.TP,
                     "LRA": 11.0, "two_pass": True},
        "alimiter": {"enabled": True},
        "fade": {"enabled": True, "in_s": 0.15, "out_s": 0.25},
    })
    ln = va.build_loudnorm(cfg, measured)
    post = va.build_post(cfg, duration)
    return ",".join(x for x in (ln, post) if x)


def main() -> int:
    ap = argparse.ArgumentParser(description="给已出成片补加 BGM（视频流 copy）")
    ap.add_argument("--video", required=True, help="已出成片（含音轨）")
    ap.add_argument("--bgm", required=True, help="BGM 文件（绝对路径或曲库内文件名）")
    ap.add_argument("--out", help="输出 mp4 路径")
    ap.add_argument("--placement", default="全程", help="全程（默认）/ 头尾")
    ap.add_argument("--gain", type=float, default=-24.0, help="BGM 音量（相对口播，dB）")
    ap.add_argument("--duck", type=float, default=12.0, help="仅「全程」：人声段压低多少 dB")
    ap.add_argument("--duck-ramp", type=float, default=0.0, dest="duck_ramp",
                    help="压低区间的斜坡秒数（0=硬台阶；0.3~0.5 听感自然）")
    ap.add_argument("--fade-in", type=float, default=1.0)
    ap.add_argument("--fade-out", type=float, default=2.0)
    ap.add_argument("--timings", help="timings.json（人声时间码；全程模式压低包络要用）")
    ap.add_argument("--offset", type=float, default=0.0,
                    help="时间码偏移秒（成片相对 timings 的前置时长，如前置 2 秒封面卡→2.0）")
    ap.add_argument("--I", type=float, default=-14.0, help="目标响度 LUFS")
    ap.add_argument("--TP", type=float, default=-1.5, help="真峰值上限 dBTP")
    ap.add_argument("--no-loudnorm", action="store_true",
                    help="跳过 loudnorm（保留原成片响度，只把 BGM 垫进去）")
    ap.add_argument("--probe-only", action="store_true", help="只打印计划，不编码")
    ap.add_argument("--bgm-only-out", dest="bgm_only_out", metavar="WAV",
                    help="另外导出「混音里的 BGM 声部本身」（用静音替掉口播）——"
                         "核验垫底音乐平不平、也可以单独听")
    a = ap.parse_args()

    video = os.path.abspath(a.video)
    bgm = os.path.abspath(a.bgm)
    if not os.path.isfile(video):
        sys.exit(f"⛔ 找不到成片：{video}")
    if not os.path.isfile(bgm):
        sys.exit(f"⛔ 找不到 BGM：{bgm}")

    total = probe_duration(video)
    print("=" * 68)
    print("给成片补加 BGM")
    print("=" * 68)
    print(f"  成片 ：{os.path.basename(video)}   时长 {total:.2f}s ({int(total//60)}:"
          f"{total%60:04.1f})")
    print(f"  BGM  ：{os.path.basename(bgm)}")

    # ---- 人声时间码 ----
    if a.timings:
        lines = load_lines(a.timings, a.offset, total)
        print(f"  时间码：{os.path.basename(a.timings)} 共 {len(lines)} 行"
              f"（offset {a.offset:+.1f}s）")
        print(f"          人声范围 {lines[0]['start']:.2f}s ~ {lines[-1]['end']:.2f}s"
              if lines else "          （无有效行）")
    else:
        vs, ve = detect_voice_bounds(video)
        lines = [{"text": "", "start": vs, "end": ve}]
        print(f"  时间码：未给 → silencedetect 兜底，人声范围 {vs:.2f}s ~ {ve:.2f}s")
        if a.placement in ("全程", "full"):
            print("          ⚠️ 兜底只有一段人声区间 → 压低包络会很粗，"
                  "「全程」模式建议给 --timings")

    plan = vb.plan(build_cfg(a), lines, total, [])
    print()
    print("【BGM 计划】")
    for ln in vb.describe(plan):
        print("  " + ln)
    if plan.get("placement") == "full":
        print(f"  压低包络段数：{len(plan.get('duck_spans') or [])}")
    fc = vb.build_filter(plan, None, total)
    print(f"  混音滤镜链长度：{len(fc)} 字符")
    if a.probe_only:
        print("\n（--probe-only：未编码）")
        return 0

    out = os.path.abspath(a.out) if a.out else os.path.splitext(video)[0] + "_BGM.mp4"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    workdir = os.path.join(os.path.dirname(out), "_过程文件")
    os.makedirs(workdir, exist_ok=True)
    mix_wav = os.path.join(workdir, "_bgm_mix.wav")

    # ---------- Stage A：混音落盘（无损 WAV） ----------
    print("\n[Stage A] 混音（口播 + BGM → WAV）")
    args = [FFMPEG, "-hide_banner", "-y", "-i", video]
    if plan.get("loop", True):
        args += ["-stream_loop", "-1"]
    args += ["-i", bgm, "-filter_complex", fc, "-map", "[aout]",
             "-t", f"{total:.3f}",
             "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", mix_wav]
    p = run(args, label=f"-> {os.path.basename(mix_wav)}")
    if p.returncode != 0:
        print((p.stderr or "")[-1500:])
        sys.exit("⛔ 混音失败")
    print(f"    ✅ {os.path.getsize(mix_wav)/1e6:.1f} MB")

    # ---------- 可选：单独导出「BGM 声部本身」（核验平不平） ----------
    if a.bgm_only_out:
        print("\n[核验] 导出 BGM 声部本身（静音替掉口播）")
        args0 = [FFMPEG, "-hide_banner", "-y", "-f", "lavfi",
                 "-i", f"anullsrc=r=48000:cl=stereo:d={total:.3f}"]
        if plan.get("loop", True):
            args0 += ["-stream_loop", "-1"]
        args0 += ["-i", bgm, "-filter_complex", fc, "-map", "[aout]",
                  "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le",
                  os.path.abspath(a.bgm_only_out)]
        p0 = run(args0, label=f"-> {os.path.basename(a.bgm_only_out)}")
        if p0.returncode != 0:
            print((p0.stderr or "")[-800:])

    # ---------- Stage B：测响度 → loudnorm → 编码 ----------
    if a.no_loudnorm:
        print("\n[Stage B] 跳过 loudnorm，仅编码音轨")
        args = [FFMPEG, "-hide_banner", "-y", "-i", video, "-i", mix_wav,
                "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out]
    else:
        print("\n[Stage B] 测响度（针对混好 BGM 的信号）")
        measured = va.analyze(mix_wav)
        chain = audio_chain(a, measured, total)
        args = [FFMPEG, "-hide_banner", "-y", "-i", video, "-i", mix_wav,
                "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                "-af", chain,
                "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out]
    p = run(args, label=f"-> {os.path.basename(out)}")
    if p.returncode != 0:
        print((p.stderr or "")[-1500:])
        sys.exit("⛔ 编码失败")

    print(f"\n✅ 出片：{out}")
    print(f"   体积 {os.path.getsize(out)/1e6:.1f} MB")

    # ---------- 实测（唯一判据） ----------
    print("\n[实测] 成片响度")
    q = run([FFMPEG, "-hide_banner", "-i", out, "-af",
             "loudnorm=print_format=summary", "-f", "null", "-"])
    for k in ("Input Integrated", "Input True Peak", "Input LRA"):
        m = re.search(rf"{k}:\s*([-\d.]+)", q.stderr or "")
        if m:
            print(f"    {k:<18} {m.group(1)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
