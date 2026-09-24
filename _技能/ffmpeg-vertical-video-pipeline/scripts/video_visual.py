# -*- coding: utf-8 -*-
r"""
画面处理 —— 段间叠化转场 / 段间色温亮度对齐 / 画面降噪

针对「分段拍、后期拼」的场景（口播稿可能分 1~N 段拍）：
    分段拍 → 拼起来必然有接缝：画面跳变、光线色温不一致、噪点水平不同
本模块解决前两个（降噪是附带的可选项）。

⭐ 支持两种输入形态，**段数完全自适应（1~N）**：
    ① 多文件（推荐）：--files a.mp4 b.mp4 c.mp4
       → 每个文件 = 一段，无需猜测，最可靠
    ② 单文件：按「段间长静音」自动切段（find_segments）
       → 适合"一口气拍完、中间有较长停顿"的情况

核心思路：
    ① 先在「剪停顿」阶段**保留段间长停顿**（不压缩）
    ② 本模块把视频切成 N 段（多文件：按文件切；单文件：按长静音切）
    ③ 逐段量测画面平均色，算出对齐增益
    ④ 每段各自 trim → 归一化 → 调色 → xfade 串联；音频用 acrossfade 同步串联

⚠️ 关键：本模块会**改变时间轴总长**（每个转场消耗 xfade_d 秒）。
   所以必须在语音识别**之前**执行，否则字幕时间码会全错。

用法：
    python video_visual.py --probe 视频.mp4              # 单文件：看分段与色温量测
    python video_visual.py --probe-multi a.mp4 b.mp4     # 多文件：看色温量测
    python video_visual.py --apply-multi a.mp4 b.mp4 -o 出.mp4
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import paths  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

FFMPEG = paths.ffmpeg_path()

# ---------------- 降噪预设 ----------------
# hqdn3d = 亮度空间:色度空间:亮度时间:色度时间，值越大越强
DENOISE_PRESETS = {
    "关闭": None,
    "轻": "hqdn3d=2:1.5:3:2.5",
    "中": "hqdn3d=4:3:6:4.5",
    "强": "hqdn3d=6:5:9:7",
}

# ---------------- 转场预设（ffmpeg xfade 的 transition 名） ----------------
TRANSITIONS = {
    "叠化": "fade",
    "黑场": "fadeblack",
    "白场": "fadewhite",
    "溶解": "dissolve",
    "左滑": "slideleft",
    "上滑": "slideup",
    "无": None,          # 硬切：不叠化，直接首尾相接
}

GAIN_LIMIT = 0.20      # 单通道增益最多 ±20%，避免把画面调歪
MIN_SEG = 0.2          # 短于此长度的段无法加转场，会被并入相邻段


def _run(args, cwd=None):
    return subprocess.run(args, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", cwd=cwd)


# ============================ ① 素材探测 ============================
def detect_silences(video: str, noise_db: float = -35.0, min_dur: float = 0.6):
    p = _run([FFMPEG, "-hide_banner", "-i", video, "-af",
              f"silencedetect=noise={noise_db}dB:d={min_dur}", "-f", "null", "-"])
    log = p.stderr or ""
    starts = [float(x) for x in re.findall(r"silence_start:\s*([0-9.]+)", log)]
    ends = [float(x) for x in re.findall(r"silence_end:\s*([0-9.]+)", log)]
    pairs = list(zip(starts, ends))
    if len(starts) > len(ends):
        pairs.append((starts[-1], None))
    return pairs


def find_segments(video: str, seg_gap: float = 1.2, noise_db: float = -35.0
                  ) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    """
    按「长于 seg_gap 的静音」把视频切成若干段。
    返回 (segments, gaps)：
        segments = [(起, 止), ...]，gaps = 段间的长静音区间
    """
    dur = probe_duration(video)
    sil = detect_silences(video, noise_db)
    gaps = []
    for s, e in sil:
        e = dur if e is None else e
        if e - s >= seg_gap:
            gaps.append((s, e))

    if not gaps:
        return [(0.0, dur)], []

    segs, cur = [], 0.0
    for s, e in gaps:
        if s - cur > 0.3:
            segs.append((cur, s))
        cur = e
    if dur - cur > 0.3:
        segs.append((cur, dur))
    return segs, gaps


def probe_duration(video: str) -> float:
    p = _run([FFMPEG, "-hide_banner", "-i", video])
    m = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", p.stderr or "")
    if not m:
        raise RuntimeError(f"无法读取时长：{video}")
    h, mi, s = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(s)


def probe_size(video: str):
    """返回 (宽, 高)"""
    p = _run([FFMPEG, "-hide_banner", "-i", video])
    m = re.search(r"Video:.*?(\d{2,5})x(\d{2,5})", p.stderr or "")
    return (int(m.group(1)), int(m.group(2))) if m else (None, None)


def probe_fps(video: str):
    p = _run([FFMPEG, "-hide_banner", "-i", video])
    m = re.search(r"(\d+(?:\.\d+)?)\s*fps", p.stderr or "")
    return float(m.group(1)) if m else None


def has_audio(video: str) -> bool:
    p = _run([FFMPEG, "-hide_banner", "-i", video])
    return "Audio:" in (p.stderr or "")


# ============================ ② 量测色温/亮度 ============================
def frame_mean_rgb(video: str, t: float, size: int = 48):
    """
    取某一时刻的一帧，缩到 size×size 后求平均 RGB。
    直接读 rawvideo 到内存，不落临时文件。
    """
    p = subprocess.run(
        [FFMPEG, "-hide_banner", "-loglevel", "error", "-ss", f"{t:.3f}",
         "-i", os.path.abspath(video), "-frames:v", "1",
         "-vf", f"scale={size}:{size}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        capture_output=True)
    buf = p.stdout or b""
    n = size * size
    if len(buf) < n * 3:
        return None
    r = sum(buf[0::3][:n]) / n
    g = sum(buf[1::3][:n]) / n
    b = sum(buf[2::3][:n]) / n
    return (r, g, b)


def measure_segment_colors(video: str, segments, samples: int = 3):
    """每段取 samples 个时间点的均值（避开段首尾，减少转场/静音影响）"""
    out = []
    for s, e in segments:
        span = e - s
        times = [s + span * f for f in
                 ([0.35, 0.5, 0.65] if samples == 3 else
                  [(i + 1) / (samples + 1) for i in range(samples)])]
        vals = [v for v in (frame_mean_rgb(video, t) for t in times) if v]
        if not vals:
            out.append((128.0, 128.0, 128.0))
        else:
            out.append(tuple(sum(v[i] for v in vals) / len(vals) for i in range(3)))
    return out


def measure_entries_colors(entries, samples: int = 3):
    """与 measure_segment_colors 同理，但每一段可以来自不同文件"""
    out = []
    for e in entries:
        s, t = float(e["start"]), float(e["end"])
        out.extend(measure_segment_colors(e["file"], [(s, t)], samples))
    return out


def compute_gains(colors, limit: float = GAIN_LIMIT):
    """
    以全体段的平均色为目标，算出每段每通道的增益。
    增益做了上下限裁剪，避免个别段被拉歪。
    """
    if len(colors) <= 1:
        return [(1.0, 1.0, 1.0) for _ in colors]
    target = [sum(c[i] for c in colors) / len(colors) for i in range(3)]
    gains = []
    for c in colors:
        g = []
        for i in range(3):
            v = target[i] / max(c[i], 1.0)
            v = max(1.0 - limit, min(1.0 + limit, v))
            g.append(round(v, 4))
        gains.append(tuple(g))
    return gains


# ============================ ③ 时间线拼接（1~N 段通用） ============================
def merge_short_entries(entries, min_len: float = MIN_SEG):
    """
    太短的段（< min_len）没法加转场，会并入前一段（否则 xfade 的 offset 会越界报错）。
    返回（合并后的 entries, 被并入的段数）
    """
    if len(entries) <= 1:
        return entries, 0
    out, merged = [], 0
    for e in entries:
        length = float(e["end"]) - float(e["start"])
        if length < min_len and out:
            prev = out[-1]
            # 只有同源文件才能直接延长区间；跨文件则丢弃该段
            if os.path.abspath(prev["file"]) == os.path.abspath(e["file"]):
                prev = dict(prev)
                prev["end"] = e["end"]
                out[-1] = prev
            merged += 1
            continue
        out.append(dict(e))
    return out, merged


def build_timeline(entries, out_path: str, gains=None, xfade_d: float = 0.25,
                   transition: str = "fade", denoise: str | None = None,
                   color_match: bool = True, crf: int = 18, preset: str = "medium",
                   out_w: int | None = None, out_h: int | None = None,
                   fps: float | None = None, audios: dict | None = None) -> str:
    """
    把若干「段」串成一条时间线。段可以来自不同文件（entries 里各自带 file）。

    entries = [{"file": 路径, "start": 起秒, "end": 止秒}, ...]

    为什么统一出口：xfade 对输入极其挑剔——分辨率、像素格式、SAR、
    帧率、时间基必须完全一致，否则会出现「命令成功但时长不对」的怪现象。
    这里把每段各自归一化后再串，从根上避免。
    """
    entries, _ = merge_short_entries(entries)
    n = len(entries)
    if n == 0:
        raise ValueError("没有任何有效片段")

    # ⚠️ 安全内置：调用方没指定统一规格时，这里自己探一遍。
    #    xfade 对输入规格极其挑剔——分辨率不一致会直接报
    #    "First input link main parameters (size AxB) do not match ..."，
    #    把这件事外包给调用方迟早会漏（实测漏过一次）。
    if not (out_w and out_h):
        auto_w, auto_h = plan_uniform_size(entries)
        if auto_w:
            out_w, out_h = auto_w, auto_h
            print(f"    ⚠️ 各段分辨率不一致 → 自动统一到 {out_w}x{out_h}")
    if not fps:
        fps = plan_uniform_fps(entries)
        if fps:
            print(f"    ⚠️ 各段帧率不一致 → 自动统一到 {fps:g}fps")

    # 建立 文件 → 输入序号 的映射（同一个文件只 -i 一次）
    files: list[str] = []
    for e in entries:
        p = os.path.abspath(e["file"])
        if p not in files:
            files.append(p)
    idx = {p: i for i, p in enumerate(files)}
    if audios is None:
        audios = {p: has_audio(p) for p in files}

    # 归一化链：尺寸（可选）→ 帧率（可选）→ 像素格式 → SAR
    norm = []
    if out_w and out_h:
        norm += [f"scale={out_w}:{out_h}:force_original_aspect_ratio=increase",
                 f"crop={out_w}:{out_h}"]
    if fps:
        norm.append(f"fps={fps:g}")
    norm += ["setsar=1", "format=yuv420p"]

    use_xfade = xfade_d > 0 and TRANSITIONS.get(transition, transition) is not None
    xf = TRANSITIONS.get(transition, transition)

    fc, vlab, alab, lens = [], [], [], []
    for i, e in enumerate(entries):
        fi = idx[os.path.abspath(e["file"])]
        s, t = float(e["start"]), float(e["end"])
        lens.append(t - s)

        chain = list(norm)
        if denoise:
            chain.append(denoise)
        if color_match and gains:
            g = gains[i]
            chain.append(f"colorchannelmixer=rr={g[0]}:gg={g[1]}:bb={g[2]}")
        fc.append(f"[{fi}:v]trim=start={s:.3f}:end={t:.3f},setpts=PTS-STARTPTS,"
                  f"settb=AVTB,{','.join(chain)}[v{i}]")

        if audios.get(os.path.abspath(e["file"]), True):
            fc.append(f"[{fi}:a]atrim=start={s:.3f}:end={t:.3f},"
                      f"asetpts=PTS-STARTPTS,aformat=sample_fmts=fltp:"
                      f"sample_rates=48000:channel_layouts=stereo[a{i}]")
        else:
            # ⚠️ 素材可能整段没有音轨（纯 B-roll），必须补静音，
            #    否则 acrossfade 引用 [N:a] 会直接失败。
            fc.append(f"anullsrc=channel_layout=stereo:sample_rate=48000,"
                      f"atrim=start=0:end={t - s:.3f},asetpts=PTS-STARTPTS[a{i}]")
        vlab.append(f"[v{i}]")
        alab.append(f"[a{i}]")

    if n == 1 or not use_xfade:
        # 无转场：直接 concat，时长完全无损
        fc.append("".join(f"{v}{a}" for v, a in zip(vlab, alab))
                  + f"concat=n={n}:v=1:a=1[vo][ao]")
        vout, aout = "[vo]", "[ao]"
    else:
        vcur = vlab[0]
        acum = lens[0]
        for i in range(1, n):
            off = max(0.0, acum - xfade_d)
            lbl = f"[vx{i}]"
            fc.append(f"{vcur}{vlab[i]}xfade=transition={xf}:"
                      f"duration={xfade_d}:offset={off:.3f}{lbl}")
            vcur = lbl
            acum = acum + lens[i] - xfade_d
        acur = alab[0]
        for i in range(1, n):
            lbl = f"[ax{i}]"
            fc.append(f"{acur}{alab[i]}acrossfade=d={xfade_d}:c1=tri:c2=tri{lbl}")
            acur = lbl
        vout, aout = vcur, acur

    args = [FFMPEG, "-hide_banner", "-y"]
    for p in files:
        args += ["-i", p]
    args += ["-filter_complex", ";".join(fc),
             "-map", vout, "-map", aout,
             "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
             "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
             os.path.abspath(out_path)]
    p = _run(args)
    if p.returncode != 0:
        print("  !! 拼接失败，最后 15 行：")
        for line in (p.stderr or "").splitlines()[-15:]:
            print(f"     {line}")
        raise RuntimeError("build_timeline 失败")
    return out_path


def xfade_segments(video: str, out_path: str, segments, gains=None,
                   xfade_d: float = 0.25, transition: str = "fade",
                   denoise: str | None = None, color_match: bool = True,
                   crf: int = 18, preset: str = "medium") -> str:
    """单文件多段的便捷包装（段=时间区间）"""
    entries = [{"file": video, "start": s, "end": e} for s, e in segments]
    return build_timeline(entries, out_path, gains, xfade_d, transition,
                          denoise, color_match, crf, preset)


def entries_from_files(files, gap_trim: float = 0.0):
    """
    多文件 → entries：每个文件整段算一段。
    gap_trim > 0 时裁掉每段末尾的静音尾巴（分段拍常见的「按停后空一会」）。
    """
    entries = []
    for f in files:
        dur = probe_duration(f)
        s, e = 0.0, dur
        if gap_trim > 0:
            # 只裁尾部纯静音，不动开头（开头常有起手字，裁早了会吃字）
            sil = detect_silences(f)
            for ss, se in reversed(sil):
                se = dur if se is None else se
                if se >= dur - 0.05 and (se - ss) >= gap_trim:
                    e = max(0.5, ss + 0.15)
                    break
        entries.append({"file": f, "start": s, "end": round(e, 3)})
    return entries


def plan_uniform_fps(entries):
    """各文件帧率不一致时，xfade 会出问题 → 取最小值统一（None=无需统一）"""
    fps_list = []
    for f in {os.path.abspath(e["file"]) for e in entries}:
        v = probe_fps(f)
        if v:
            fps_list.append(round(v, 3))
    if len(set(fps_list)) <= 1:
        return None
    return min(fps_list)


def plan_uniform_size(entries):
    """
    各文件分辨率不一致时统一到「目标竖屏尺寸」。
    一致则不缩放（避免无谓的重采样损失）。
    """
    sizes = []
    for f in {os.path.abspath(e["file"]) for e in entries}:
        w, h = probe_size(f)
        if w and h:
            sizes.append((w, h))
    if len(set(sizes)) <= 1:
        return (None, None)
    return (OUT_W, OUT_H)


OUT_W, OUT_H = 1080, 1920      # 目标竖屏尺寸（仅在不同分辨率混剪时才用到）


# ============================ ④ 诊断与 CLI ============================
def health_check(n_segs: int, dur: float, mode: str) -> list[str]:
    """
    段数合理性提醒。
    ⚠️ 单文件模式下「只切出 1 段」有两种可能：a) 确实没分段拍；b) 静音没检出来。
       后者最常见的原因是环境底噪盖过了 -35dB 阈值 → 叠化会静默失效。
       这里主动提示，避免「以为做了叠化其实没做」。
    """
    tips = []
    if mode == "single" and n_segs == 1 and dur > 45:
        tips.append(f"只切出 1 段，但素材长达 {dur:.0f}s——")
        tips.append("  如果你是分段拍的（比如 2~3 段），说明段间停顿没被检出，两条路：")
        tips.append("    · 调高静音灵敏度：--noise-db -28（有底噪/混响时常用 -25~-30）")
        tips.append("    · 或调小判定秒数：--seg-gap 0.8")
        tips.append("  ⭐ 更可靠的做法：直接传多个文件（每个文件一段），无需猜测")
    if mode == "single" and n_segs > 8:
        tips.append(f"切出 {n_segs} 段偏多——可能是把「思考停顿」也当成了段间停顿。")
        tips.append("  建议调大 --seg-gap（如 2.0~3.0），或改用多文件模式")
    return tips


def report_colors(colors, gains) -> None:
    print("\n  各段平均 RGB（0-255）：")
    for i, c in enumerate(colors):
        print(f"    {i+1}. R{c[0]:6.1f}  G{c[1]:6.1f}  B{c[2]:6.1f}")
    if gains:
        print(f"\n  对齐增益（单通道上限 ±{GAIN_LIMIT*100:.0f}%）：")
        delta = []
        for i, g in enumerate(gains):
            d = max(abs(g[j] - 1.0) for j in range(3))
            delta.append(d)
            print(f"    {i+1}. rr={g[0]:.4f}  gg={g[1]:.4f}  bb={g[2]:.4f}")
        worst = max(delta) if delta else 0
        print(f"\n  → 最大需修正 {worst*100:.1f}%"
              + ("（差异小，可不开色温对齐）" if worst < 0.03
                 else "（差异明显，建议开启色温对齐）" if worst < GAIN_LIMIT
                 else "（差异很大，已触上限，可能需要手动调）"))


def cmd_probe(video: str, seg_gap: float, noise_db: float, denoise: str):
    print("=" * 74)
    print(f"单文件分段探测：{video}")
    print("=" * 74)
    dur = probe_duration(video)
    print(f"  总长 {dur:.2f}s")
    segs, gaps = find_segments(video, seg_gap, noise_db)
    print(f"\n  按「静音 ≥ {seg_gap}s / 阈值 {noise_db}dB」切分，得到 {len(segs)} 段"
          f"（段间长停顿 {len(gaps)} 处）：")
    for i, (s, e) in enumerate(segs):
        print(f"    {i+1}. {s:8.2f} - {e:8.2f}   ({e-s:6.2f}s)")
    for s, e in gaps:
        print(f"       段间停顿 {s:8.2f} - {e:8.2f}   ({e-s:5.2f}s)")

    for t in health_check(len(segs), dur, "single"):
        print(f"  {t}")

    if len(segs) < 2:
        print("\n  → 只有一段，无叠化需求")
        return

    colors = measure_segment_colors(video, segs)
    gains = compute_gains(colors)
    report_colors(colors, gains)

    print(f"\n  计划处理：{len(segs)} 段，叠化 0.25s×{len(segs)-1}，"
          f"预计成片 {dur - 0.25*(len(segs)-1):.2f}s")
    print(f"  降噪：{denoise}  ->  {DENOISE_PRESETS.get(denoise) or '（不降噪）'}")
    print()
    print("  实际试跑：")
    print(f'    python video_visual.py --apply "{video}" 输出.mp4 --seg-gap {seg_gap}')


def cmd_probe_multi(files, denoise: str, xfade: float, transition: str):
    print("=" * 74)
    print(f"多文件模式探测：{len(files)} 个文件 → {len(files)} 段")
    print("=" * 74)
    entries = entries_from_files(files)
    total = 0.0
    for i, e in enumerate(entries):
        d = e["end"] - e["start"]
        total += d
        w, h = probe_size(e["file"])
        fps = probe_fps(e["file"])
        au = "有" if has_audio(e["file"]) else "⚠️ 无"
        print(f"    {i+1}. {os.path.basename(e['file'])}")
        print(f"       {d:7.2f}s   {w}x{h}  {fps:g}fps  音轨:{au}")

    fps_u = plan_uniform_fps(entries)
    w_u, h_u = plan_uniform_size(entries)
    if fps_u:
        print(f"\n  ⚠️ 帧率不一致 → 将统一到 {fps_u:g}fps")
    if w_u:
        print(f"  ⚠️ 分辨率不一致 → 将统一到 {w_u}x{h_u}")
    if not fps_u and not w_u:
        print("\n  ✅ 各段规格一致，无需归一化")

    colors = measure_entries_colors(entries)
    gains = compute_gains(colors)
    report_colors(colors, gains)

    xf = TRANSITIONS.get(transition, transition)
    n = len(entries)
    if xf:
        print(f"\n  计划：{n} 段，转场「{transition}」{xfade}s × {n-1}，"
              f"预计成片 {total - xfade*(n-1):.2f}s")
    else:
        print(f"\n  计划：{n} 段，硬切（无转场），预计成片 {total:.2f}s")
    print(f"  降噪：{denoise}  ->  {DENOISE_PRESETS.get(denoise) or '（不降噪）'}")
    print()
    print("  实际试跑：")
    print("    python video_visual.py --files " + " ".join(f'"{f}"' for f in files)
          + " --out 输出.mp4")


def _do_multi(files, out_path, args) -> str:
    entries = entries_from_files(files, args.trim_tail)
    print(f"  共 {len(entries)} 段")
    fps_u = plan_uniform_fps(entries)
    w_u, h_u = plan_uniform_size(entries)
    gains = None
    if not args.no_color_match and len(entries) > 1:
        gains = compute_gains(measure_entries_colors(entries))
        print("  色温对齐增益：" + " ".join(
            f"({g[0]:.3f},{g[1]:.3f},{g[2]:.3f})" for g in gains))
    build_timeline(entries, out_path, gains, args.xfade, args.transition,
                   DENOISE_PRESETS.get(args.denoise), not args.no_color_match,
                   args.crf, "medium", w_u, h_u, fps_u)
    print(f"  完成：{out_path}  ({probe_duration(out_path):.2f}s)")
    return out_path


def main():
    ap = argparse.ArgumentParser(description="画面处理：段间叠化 / 色温对齐 / 降噪")
    ap.add_argument("--probe", metavar="视频", help="单文件：看分段与量测结果")
    ap.add_argument("--probe-multi", nargs="+", metavar="视频", help="多文件：看量测结果")
    ap.add_argument("--apply", nargs=2, metavar=("输入", "输出"), help="单文件：实际处理")
    ap.add_argument("--files", nargs="+", metavar="视频", help="多文件：实际处理（配 --out）")
    ap.add_argument("--out", metavar="输出", help="多文件模式的输出路径")
    ap.add_argument("--seg-gap", type=float, default=1.2, help="判定段间的静音秒数")
    ap.add_argument("--noise-db", type=float, default=-35.0,
                    help="静音阈值；有底噪/混响时用 -25 ~ -30")
    ap.add_argument("--trim-tail", type=float, default=0.0,
                    help="多文件模式：裁掉每段尾部的静音（秒），0=不裁")
    ap.add_argument("--denoise", default="关闭", choices=list(DENOISE_PRESETS))
    ap.add_argument("--transition", default="叠化", choices=list(TRANSITIONS))
    ap.add_argument("--xfade", type=float, default=0.25, help="转场时长秒；0=硬切")
    ap.add_argument("--crf", type=int, default=18)
    ap.add_argument("--no-color-match", action="store_true")
    args = ap.parse_args()

    if args.probe:
        cmd_probe(args.probe, args.seg_gap, args.noise_db, args.denoise)
        return

    if args.probe_multi:
        cmd_probe_multi(args.probe_multi, args.denoise, args.xfade, args.transition)
        return

    if args.files:
        if not args.out:
            ap.error("--files 需要同时给 --out <输出路径>")
        _do_multi(args.files, args.out, args)
        return

    if args.apply:
        src, dst = args.apply
        segs, gaps = find_segments(src, args.seg_gap, args.noise_db)
        print(f"切出 {len(segs)} 段，段间停顿 {len(gaps)} 处")
        for t in health_check(len(segs), probe_duration(src), "single"):
            print(f"  {t}")
        gains = None
        if not args.no_color_match and len(segs) > 1:
            gains = compute_gains(measure_segment_colors(src, segs))
            print("对齐增益：" + "  ".join(f"({g[0]},{g[1]},{g[2]})" for g in gains))
        xfade_segments(src, dst, segs, gains, args.xfade, args.transition,
                       DENOISE_PRESETS.get(args.denoise),
                       not args.no_color_match)
        print(f"完成：{dst}  ({probe_duration(dst):.2f}s)")
        return

    print(__doc__)


if __name__ == "__main__":
    main()
