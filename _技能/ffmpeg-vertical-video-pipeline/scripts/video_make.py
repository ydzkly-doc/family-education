# -*- coding: utf-8 -*-
r"""
视频合成主控 —— 把「口播素材 + 文案」变成可直接发布的竖屏成片（1080x1920）

全程 ffmpeg，不依赖剪映（剪映 11.5 强制加密草稿，写文件生成工程已实测不可行）。

流水线：
  ① 剪停顿（silencedetect 长静音 → trim/concat 掐掉；**段间长停顿保留**供②切段）
  ② 画面处理（段间叠化 xfade / 段间色温亮度对齐 / 画面降噪 hqdn3d）
  ③ 取时间码（faster-whisper；有文案则只取时间码并与文案全局对齐）
  ④ 生成 ASS 字幕（全程字幕 / 序号条 / 金句大字卡；含 CJK 自动折行与淡入动画）
  ⑤ 音频美化（降噪/去齿音/音色塑形/响度标准化/真峰值限制/**首尾淡入淡出**）
  ⑥ 烧字幕合成 + 缩放裁切到 1080x1920
  ⑦ 出封面图

⛔ 顺序铁律：② 必须在 ③ 之前。转场会缩短总时长（每个吃掉 xfade 秒），
   若在语音识别之后才做，字幕时间码会整体错位。

用法（最少参数即走标准能力）：
  python video_make.py --video 素材.mp4 --script 文案.txt --out 成片.mp4

动态调参（不改文件，Agent 可直接用）：
  --set audio.arnndn.mix=0.9
  --set audio.loudnorm.I=-13
  --set visual.denoise=轻 --set visual.xfade=0.3
  --audio-preset 标准|轻|强|仿剪映声音美化|关闭
  --denoise 关闭|轻|中|强      画面降噪
  --transition 叠化|黑场|白场|溶解|左滑|上滑
  --seg-gap 1.2                静音 ≥ 此秒数即视为「段间停顿」→ 切段并叠化
  --no-visual                  关闭全部画面处理

查看：
  --dump-params   打印最终生效参数
  --show-chain    打印实际 ffmpeg 滤镜链（核对用）
  --list-presets  列出预设与全部可覆盖参数路径
  --spec 剪辑单.json   从 JSON 载入（其余 CLI 参数仍可覆盖）

关键工程注意（都实测踩过，改代码前务必读 SKILL.md 的「硬坑」节）：
  · ffmpeg 滤镜参数用 ':' 分隔，Windows 路径 'C:\' 会被吃坏
    → 一律把 cwd 切到目标文件所在目录、只传文件名
  · 用 subprocess 传 list，不经过 shell（中文路径 + 特殊字符才安全）
  · 字幕必须自动折行，否则 CJK 满宽字符会溢出画面被裁
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import io
import shutil

# 原地改编码，避免与其它模块叠加包装（见 video_build_ass.py 同名说明）
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import paths  # noqa: E402
from video_build_ass import (build_ass, safe_check, WARM, WARM_DEEP,   # noqa: E402
                             PLAY_RES_X, PLAY_RES_Y)

FFMPEG = paths.ffmpeg_path()
OUT_W, OUT_H = 1080, 1920


def run(args, cwd=None, label=""):
    """统一调用 ffmpeg：list 传参、不经 shell"""
    if label:
        print(f"    · {label}")
    p = subprocess.run(args, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", cwd=cwd)
    if p.returncode != 0:
        print(f"    !! 失败（退出码 {p.returncode}）")
        for line in (p.stderr or "").splitlines()[-12:]:
            print(f"       {line}")
        raise RuntimeError(f"ffmpeg 失败：{label}")
    return p


# ---------------- ① 剪停顿 ----------------
def detect_silences(video: str, noise_db: float = -35.0, min_dur: float = 0.6):
    p = subprocess.run(
        [FFMPEG, "-hide_banner", "-i", video, "-af",
         f"silencedetect=noise={noise_db}dB:d={min_dur}", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    log = p.stderr or ""
    starts = [float(x) for x in re.findall(r"silence_start:\s*([0-9.]+)", log)]
    ends = [float(x) for x in re.findall(r"silence_end:\s*([0-9.]+)", log)]
    pairs = list(zip(starts, ends))
    if len(starts) > len(ends):          # 结尾处静音可能没有 end
        pairs.append((starts[-1], None))
    return pairs


def build_keep_intervals(duration: float, silences, keep_gap: float = 0.35,
                         min_cut: float = 0.8, preserve_above: float | None = None,
                         keep_edges: bool = False):
    """
    把 [min_cut, preserve_above) 之间的静音压缩到 keep_gap 秒；短于 min_cut 的原样保留
    （那是自然停顿，不该动）。

    ⚠️ preserve_above：**长于它的静音完全不动**。
      这是「分段拍」场景的关键——段与段之间的长停顿要留着，
      后续才能据此切分出各段并做叠化转场（见 video_visual.py）。

    ⚠️ keep_edges：**贴在片头/片尾的静音原样保留**（不压缩）。
      这是「BGM 只垫头尾」的前提：头尾那块静音**就是 BGM 的位置**，
      压缩到 0.35s 后 BGM 就没有落点、会直接报「头尾太短」。
    """
    cuts = []
    for s, e in silences:
        e = duration if e is None else e
        length = e - s
        if length <= min_cut:
            continue
        if preserve_above is not None and length >= preserve_above:
            continue                      # 段间长停顿，保留原样
        if keep_edges and (s <= 0.05 or e >= duration - 0.05):
            continue                      # 头/尾静音：BGM 要在这里响
        # 两侧各留 keep_gap/2
        cs = s + keep_gap / 2
        ce = e - keep_gap / 2
        if ce > cs:
            cuts.append((cs, ce))
    if not cuts:
        return [(0.0, duration)]

    keep, cur = [], 0.0
    for cs, ce in cuts:
        if cs > cur:
            keep.append((cur, cs))
        cur = ce
    if cur < duration:
        keep.append((cur, duration))
    # 丢掉过短的碎片
    return [(a, b) for a, b in keep if b - a > 0.15]


def cut_silence(video: str, out_path: str, keep_gap=0.35, min_cut=0.8,
                preserve_above: float | None = None, keep_edges: bool = False):
    """
    返回 (输出路径, keep 区间列表)。
    keep 是「保留下来的原时间区间」——有了它就能把「剪停顿前」的任意时间点
    换算到「剪停顿后」的新时间轴（见 map_time），卡片锚点定位依赖这个。
    """
    dur = probe_duration(video)
    sil = detect_silences(video)
    keep = build_keep_intervals(dur, sil, keep_gap, min_cut, preserve_above, keep_edges)
    print(f"    原长 {dur:.2f}s，检出静音 {len(sil)} 段"
          + (f"（其中 ≥{preserve_above}s 的段间停顿保留不动）" if preserve_above else "")
          + ("（头尾静音保留，供 BGM 落点）" if keep_edges else "")
          + f"，保留 {len(keep)} 段")

    if len(keep) == 1 and abs(keep[0][1] - dur) < 0.05:
        print("    无需剪切，直接复用原素材")
        shutil.copy(video, out_path)
        return out_path, [(0.0, dur)]

    parts, fc = [], []
    for i, (a, b) in enumerate(keep):
        fc.append(f"[0:v]trim=start={a:.3f}:end={b:.3f},setpts=PTS-STARTPTS[v{i}];"
                  f"[0:a]atrim=start={a:.3f}:end={b:.3f},asetpts=PTS-STARTPTS[a{i}]")
        parts.append(f"[v{i}][a{i}]")
    fc.append("".join(parts) + f"concat=n={len(keep)}:v=1:a=1[vo][ao]")

    run([FFMPEG, "-hide_banner", "-y", "-i", video,
         "-filter_complex", ";".join(fc),
         "-map", "[vo]", "-map", "[ao]",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
         "-c:a", "aac", "-b:a", "192k", out_path],
        label=f"剪掉长静音 -> {os.path.basename(out_path)}")
    return out_path, keep


def map_time(t: float, keep) -> float:
    """
    把「剪停顿前」的时间点换算到「剪停顿后」的新时间轴。
    ⚠️ 多文件模式的段边界是在拼接时算的，而②剪停顿会改变时间轴，
       所以卡片用 seg 锚点时必须过这道换算，否则会偏。
    """
    out = 0.0
    for a, b in keep:
        if t <= a:
            return out
        if t >= b:
            out += b - a
        else:
            return out + (t - a)
    return out


def probe_duration(video: str) -> float:
    p = subprocess.run([FFMPEG, "-hide_banner", "-i", video],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", p.stderr or "")
    if not m:
        raise RuntimeError("无法读取素材时长")
    h, mi, s = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(s)


# ---------------- 编码参数 ----------------
def bitrate_arg(v) -> str | None:
    """把 8 / '8M' / '8000k' 统一成 ffmpeg 认的写法（裸数字 <100 视为 Mbps）"""
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    try:
        n = float(s)
    except ValueError:
        return s
    return f"{int(n * 1000)}k" if n < 100 else f"{int(n)}"


def probe_fps(path: str, default: float = 30.0) -> float:
    """
    探测视频帧率。`zoompan` 必须显式拿到 fps 参数，否则会被强制成默认 25fps。

    ⚠️ 只能用裸 `subprocess.run`：`ffmpeg -i 文件`（仅探测、无输出）
       **必然返回非零退出码**（"At least one output file must be specified"），
       走封装好的 `run()` 会直接抛错（实测踩过）。
    """
    p = subprocess.run([FFMPEG, "-hide_banner", "-i", path],
                       capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    m = re.search(r"(\d+(?:\.\d+)?)\s*fps", p.stderr or "")
    if not m:
        return default
    try:
        v = float(m.group(1))
        return v if 1 <= v <= 240 else default
    except ValueError:
        return default


def _ken_burns_filter(video: str, zoom: float, w: int, h: int) -> str:
    r"""
    画面「轻微推近」（Ken Burns）：整片从 1.0 匀速推到 `1+zoom`。

    ⚠️ `zoompan` 的三个必要参数（少一个就出问题）：
      · `d=1`  每个输入帧输出 1 帧 —— 保持时长不变（默认会一帧变 N 帧）
      · `fps=` **必须显式给**，否则被强制成 25fps（帧率被悄悄改掉）
      · `s=`   输出尺寸，与输入一致，避免二次缩放
    ⚠️ `x`/`y`/`z` 表达式里含逗号 —— 必须用单引号包住，
       否则会被 ffmpeg 的滤镜参数分隔符切开（同类坑见硬坑清单第 1 条）。
    ⚠️ 这个滤镜**每帧都要重采样**，会明显拖慢编码，只在需要时开。
    """
    fps = probe_fps(video)
    dur = probe_duration(video)
    frames = max(1, int(round(dur * fps)))
    zmax = 1.0 + float(zoom)
    return (
        f"zoompan=z='min(1+{float(zoom):.4f}*on/{frames},{zmax:.4f})'"
        f":d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        f":s={w}x{h}:fps={fps:g}"
    )


# ---------------- ④ 合成 ----------------
def mix_bgm(video: str, bgm_plan: dict, pre_chain: str | None, cwd: str | None,
            out_wav: str, total: float) -> str:
    """
    **Stage A**：把「口播前置链 + BGM」混成一条音轨，输出无损 WAV。

    ⛔ 为什么必须单独一个阶段（不能和 loudnorm 塞进同一条命令）：
       loudnorm 两遍法要**先测量再补偿**，而测量必须针对**混了 BGM 之后**的信号——
       否则它按"纯口播"的响度去补，加进来的 BGM 能量会让成片整体偏响/偏轻。
       所以：① 先混音落盘 → ② 测量这个文件 → ③ 再上 loudnorm 合成。

    ⚠️ 用 WAV（pcm_s16le）而非 AAC：这一步是有损编码前的中间产物，
       多一次 AAC 会白白损失一次音质。
    ⚠️ cwd 需指向 workdir —— arnndn 的 `.rnnn` 必须以文件名出现。
    """
    import video_bgm as vb
    fc = vb.build_filter(bgm_plan, pre_chain, total)
    args = [FFMPEG, "-hide_banner", "-y", "-i", os.path.abspath(video)]
    if bgm_plan.get("loop", True):
        # 音乐短于视频时循环补足（-stream_loop 必须在 -i 之前）
        args += ["-stream_loop", "-1"]
    args += ["-i", os.path.abspath(bgm_plan["path"]),
             "-filter_complex", fc, "-map", "[aout]",
             "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le",
             os.path.abspath(out_wav)]
    run(args, cwd=cwd, label=f"BGM 混音 -> {os.path.basename(out_wav)}")
    return out_wav


def compose(video: str, ass_path: str, out_path: str, audio_chain: str | None = None,
            cwd: str | None = None, crf=18, preset="medium", bitrate=None,
            ext_audio: str | None = None, zoom: float = 0.0):
    """
    缩放裁切到 1080x1920 + （可选）画面轻微推近 + 烧 ASS 字幕 +（可选）音频处理链。

    编码策略（视频号会二次压缩，源文件不要太寒酸）：
      · 默认 CRF（质量优先）+ `-maxrate 12M` 约束峰值（别超出平台上限）
      · 给了 `bitrate` 则改用平均码率（ABR），适合"明知平台建议 6~10Mbps"时直接对齐
      · 固定 `-profile:v high -level 4.0`（兼容性最好，避免部分机型解不了）

    ext_audio：用**外部音轨**（BGM 混音后的 WAV）替换视频自带音轨。
      给了它就必须显式 `-map`，否则 ffmpeg 可能挑错流；
      此时 audio_chain 只应含 **loudnorm + 限制器**（前置链已在 Stage A 做过）。

    zoom：>0 时启用 Ken Burns 轻微推近（如 0.06 = 推到 1.06）。
      ⚠️ 顺序是 `scale → crop → zoompan → ass` —— **推近必须在烧字幕之前**，
         否则字幕会跟着一起放大。

    cwd 说明：ass 与 arnndn 的 .rnnn 模型都必须以「文件名」形式出现在滤镜里，
    否则 Windows 盘符的冒号会破坏滤镜参数解析。故调用方需保证两者都在 cwd 下。
    """
    ass_name = os.path.basename(ass_path)
    work = cwd or os.path.dirname(os.path.abspath(ass_path))
    # 把 ass 放到 cwd（若已在则跳过）
    if os.path.dirname(os.path.abspath(ass_path)) != os.path.abspath(work):
        shutil.copy(ass_path, os.path.join(work, ass_name))

    vparts = [f"scale={OUT_W}:{OUT_H}:force_original_aspect_ratio=increase",
              f"crop={OUT_W}:{OUT_H}"]
    if zoom and float(zoom) > 0.001:
        vparts.append(_ken_burns_filter(video, float(zoom), OUT_W, OUT_H))
    vparts.append(f"ass={ass_name}")
    vf = ",".join(vparts)
    # ⚠️ 所有 -i 必须在 -vf 之前（踩过两次：否则 -vf 会被当成下一个输入的选项）
    args = [FFMPEG, "-hide_banner", "-y", "-i", os.path.abspath(video)]
    if ext_audio:
        args += ["-i", os.path.abspath(ext_audio)]
    args += ["-vf", vf]
    if ext_audio:
        args += ["-map", "0:v", "-map", "1:a"]
    if audio_chain:
        args += ["-af", audio_chain]
    args += ["-c:v", "libx264", "-preset", preset]
    br = bitrate_arg(bitrate)
    if br:
        args += ["-b:v", br, "-maxrate", br, "-bufsize", "16M"]
    else:
        args += ["-crf", str(crf), "-maxrate", "12M", "-bufsize", "24M"]
    args += ["-profile:v", "high", "-level", "4.0",
             "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
             os.path.abspath(out_path)]
    run(args, cwd=work, label=f"合成 -> {os.path.basename(out_path)}")
    return out_path


# ---------------- ⑤ 封面 ----------------
def make_cover(spec: dict, ass_dir: str, out_png: str, at: float = 0.0):
    """
    出**两张**封面：
      · `cover.png`      9:16 全屏版（与视频里的金句卡同一套样式）
      · `cover_1x1.png`  **1:1 方版** —— 视频号在朋友圈分享时按 1:1 裁切，
                         搜一搜缩略图也用它，所以必须单独出一张（别让平台替你裁）

    ⚠️ 1:1 是**单独渲染**的（画布就是 1080×1080），不是把 9:16 裁一刀——
       那样文字会被裁掉。
    """
    cover = spec.get("cover")
    if not cover:
        return None
    src = spec.get("video")
    # ⚠️ 封面是**静帧**，必须关掉淡入（anim=""）——
    #    否则渲染 t=0 时 \fad 还没开始，抓到的是**完全透明的空画面**（实测踩过，封面一直是白的）
    cspec = {"punch": [{"start": 0.0, "end": 2.0, "text": cover["text"],
                        "marks": cover.get("marks"), "anim": ""}]}
    outs = []

    # ① 9:16 全屏
    cpath = os.path.join(ass_dir, "_cover.ass")
    build_ass(cspec, cpath, wrap=True)
    run([FFMPEG, "-hide_banner", "-y", "-ss", f"{at:.2f}", "-i", os.path.abspath(src),
         "-vf", f"scale={OUT_W}:{OUT_H}:force_original_aspect_ratio=increase,"
                f"crop={OUT_W}:{OUT_H},ass={os.path.basename(cpath)}",
         "-frames:v", "1", os.path.abspath(out_png)],
        cwd=ass_dir, label=f"封面 9:16 -> {os.path.basename(out_png)}")
    outs.append(out_png)

    # ② 1:1 方版（画面取中间方形，文字按方形画布重新排）
    sq_png = os.path.join(os.path.dirname(out_png), "cover_1x1.png")
    sq_ass = os.path.join(ass_dir, "_cover_1x1.ass")
    sq_cspec = dict(cspec)
    sq_cspec["play_res"] = [1080, 1080]      # 画布就是方形，文字按方形折行
    build_ass(sq_cspec, sq_ass, wrap=True)
    run([FFMPEG, "-hide_banner", "-y", "-ss", f"{at:.2f}", "-i", os.path.abspath(src),
         "-vf", f"scale=1080:1080:force_original_aspect_ratio=increase,"
                f"crop=1080:1080,ass={os.path.basename(sq_ass)}",
         "-frames:v", "1", os.path.abspath(sq_png)],
        cwd=ass_dir, label=f"封面 1:1 -> {os.path.basename(sq_png)}")
    outs.append(sq_png)
    return outs


# ---------------- 卡片定位（锚点 / 段号 / 秒数） ----------------
def _key(s: str) -> str:
    """去掉标点空白，只留字与词，用于宽松比对"""
    return re.sub(r"[^\w\u4e00-\u9fff]", "", s or "")


def find_line_by_text(text: str, lines):
    """
    在字幕行里找「含该文本」的一句，返回行下标（找不到返回 None）。
    先用精确包含，再退一步做相似度匹配（容忍 ASR 的个别错字）。
    """
    import difflib
    k = _key(text)
    if not k or not lines:
        return None
    for i, ln in enumerate(lines):
        if k in _key(ln.get("text", "")):
            return i
    best, bi = 0.0, None
    for i, ln in enumerate(lines):
        r = difflib.SequenceMatcher(None, k, _key(ln.get("text", ""))).ratio()
        if r > best:
            best, bi = r, i
    return bi if best >= 0.62 else None


def seg_bounds_of(lens, xfade_d: float):
    """由各段长度算出拼接后（含转场消耗）每段的起止时间"""
    out, cur = [], 0.0
    for i, L in enumerate(lens):
        s = cur
        e = s + L
        out.append((round(s, 3), round(e, 3)))
        cur = e - xfade_d          # 下一段头被转场吃掉 xfade_d
    return out


def resolve_place(item: dict, lines, seg_bounds, default_hold: float,
                  follow_anchor: bool = False, total_dur: float | None = None):
    """
    把一张卡片/字幕的「位置描述」翻成 (start, end) 秒。
    返回 ((start, end), 错误原因, 命中的字幕行或 None)。

    支持六种给法（推荐顺序）：
      anchor: "某句话"   → 自动找到那句字幕，**不写秒数**（改文案也还准）
      index: 3          → 第 3 行字幕（1 起）
      seg: 2            → 第 2 段开头（配合 ± offset 微调）
      at: "end"         → 片尾倒数若干秒
      start: 12.5       → 硬写秒数（最不推荐，素材一变就错位）
      to_end: true      → **一直显示到片尾**（配 at:"end" 可做"片尾定格卡，方便截图"）

    follow_anchor=True 时（精选字幕用）：时长自动**跟随那句话**，
    而不是用固定 default_hold —— 字幕要和口播同步说完。
    """
    # ① 文本锚点
    if item.get("anchor"):
        i = find_line_by_text(str(item["anchor"]), lines)
        if i is None:
            return None, f"锚点文本「{item['anchor']}」在字幕里找不到", None
        ln = lines[i]
        s, e = _span(ln, item, default_hold, follow_anchor)
        return (s, _to_end(item, e, total_dur)), None, ln

    # ② 行号
    if item.get("index") is not None:
        k = int(item["index"]) - 1
        if not lines:
            return None, "无字幕行，无法用 index 定位", None
        if not (0 <= k < len(lines)):
            return None, f"行号 {item['index']} 超出范围（共 {len(lines)} 行）", None
        ln = lines[k]
        s, e = _span(ln, item, default_hold, follow_anchor)
        return (s, _to_end(item, e, total_dur)), None, ln

    # ③ 段号锚点
    if item.get("seg") is not None and seg_bounds:
        k = int(item["seg"]) - 1
        if not (0 <= k < len(seg_bounds)):
            return None, f"段号 {item['seg']} 超出范围（共 {len(seg_bounds)} 段）", None
        hold = float(item.get("hold", default_hold))
        s = max(0.0, seg_bounds[k][0] + float(item.get("offset", 0.0)))
        return (s, _to_end(item, s + hold, total_dur)), None, None

    # ④ 片尾
    if item.get("at") == "end":
        if not lines:
            return None, "无字幕行，无法用 at='end' 定位（改用 start 或 seg）", None
        last = float(lines[-1]["end"])
        hold = float(item.get("hold", 4.0))
        tail = float(item.get("tail", 2.5))
        return (max(0.0, last - hold), _to_end(item, last + tail, total_dur)), None, None

    # ⑤ 显式秒数
    if item.get("start") is not None:
        s = float(item["start"])
        e = float(item["end"]) if item.get("end") is not None \
            else s + float(item.get("hold", default_hold))
        return (s, _to_end(item, e, total_dur)), None, None

    if item.get("at") is not None and isinstance(item.get("at"), (int, float)):
        s = float(item["at"])
        return (s, _to_end(item, s + float(item.get("hold", default_hold)),
                           total_dur)), None, None

    return None, "没有位置信息（需 anchor / index / seg / at / start 之一）", None


def _to_end(item, end: float, total_dur: float | None) -> float:
    """
    to_end=true → **一直显示到片尾结束**（片尾定格卡用）。
    ⚠️ 这里要精确等于片长，不能用 max(end, total_dur)——
       那样卡片时间会超出片尾（实测多出 2.5s，虽然不显示但落点表会很难看，
       而且以后若加了"延长片尾"的逻辑就会真的多出黑屏）。
    """
    if item.get("to_end") and total_dur:
        return float(total_dur)
    return end


MIN_SUB_HOLD = 1.2      # 精选字幕的最短显示时长（太短看不清）


def _span(ln, item, default_hold: float, follow_anchor: bool):
    """由命中的字幕行算出显示区间（lead 在三种情形下都生效）"""
    s0, e0 = float(ln["start"]), float(ln["end"])
    lead = float(item.get("lead", 0.0))
    s = max(0.0, s0 - lead)
    if item.get("hold") is not None:
        return (s, s + float(item["hold"]))
    if follow_anchor:
        # 跟随那句话；太短的话补到 MIN_SUB_HOLD 以便看清
        return (s, max(e0, s + MIN_SUB_HOLD))
    return (s, s + default_hold)


def resolve_overlaps(cards, kind: str = "卡片", min_dur: float = 1.2,
                     gap: float = 0.05):
    """
    ⚠️ 卡片时间重叠 = 两条 Dialogue 同时显示 = **文字叠字**（实测踩过）。
    这里按起点排序后依次错开：优先裁前一张的尾巴；裁不动（会短于 min_dur）
    就把后一张整体往后推。返回处理后的列表。
    """
    if len(cards) <= 1:
        return cards
    cards = sorted(cards, key=lambda c: c["start"])
    fixed = 0
    for i in range(len(cards) - 1):
        cur, nxt = cards[i], cards[i + 1]
        if cur["end"] + gap <= nxt["start"]:
            continue
        room = nxt["start"] - gap - cur["start"]      # 裁到刚好相接能给多长
        if room >= min_dur:
            cur["end"] = round(float(nxt["start"]) - gap, 3)
        else:
            shift = round((float(cur["start"]) + min_dur + gap) - float(nxt["start"]), 3)
            nxt["start"] = round(float(nxt["start"]) + shift, 3)
            nxt["end"] = round(float(nxt["end"]) + shift, 3)
            cur["end"] = round(float(cur["start"]) + min_dur, 3)
        fixed += 1
    if fixed:
        print(f"    ⚠️ {kind}有 {fixed} 处时间重叠，已自动错开（重叠会导致文字叠字）")
    return cards


def place_cards(raw, lines, seg_bounds, kind: str, default_hold: float,
                total_dur: float | None = None, follow_anchor: bool = False,
                fill_text: bool = False, base_marks=None):
    """
    raw 可以是单个 dict 或 dict 列表（卡片可能有 1~N 张）。
    返回可交给 build_ass 的列表，位置已解析、重叠已错开。

    fill_text=True：没给 `text` 的项，自动用锚点命中那行的**原文**——
    精选字幕就靠这个（**只写锚点，字幕内容照抄原句**）。
    """
    if not raw:
        return []
    items = raw if isinstance(raw, list) else [raw]
    out, failed = [], []
    for it in items:
        if not isinstance(it, dict):
            continue
        p = dict(it)
        pos, err, src = resolve_place(p, lines, seg_bounds, default_hold,
                                      follow_anchor, total_dur)
        if pos is None:
            failed.append((p.get("text") or p.get("anchor") or p.get("index", ""), err))
            continue
        p["start"], p["end"] = pos
        if fill_text and not p.get("text") and src is not None:
            p["text"] = src["text"]
        if base_marks is not None and not p.get("marks"):
            p["marks"] = base_marks
        for k in ("seg", "offset", "anchor", "index", "hold", "lead", "tail",
                  "at", "to_end"):
            p.pop(k, None)
        if not p.get("text"):
            failed.append(("(空文本)", "既没给 text，锚点也没命中"))
            continue
        out.append(p)
    for txt, err in failed:
        print(f"    ⚠️ {kind}「{str(txt)[:16]}」定位失败：{err}")
    if failed and lines:
        print("       可用的字幕行（取前 12 行，供改锚点参考）：")
        for ln in lines[:12]:
            print(f"         [{float(ln['start']):7.2f}] {ln['text'][:28]}")
    out = resolve_overlaps(out, kind)
    if total_dur:
        for c in out:
            if float(c["start"]) > total_dur - 0.3:
                print(f"    ⚠️ {kind}「{str(c.get('text', ''))[:16]}」起点 "
                      f"{c['start']:.1f}s 已超过片长 {total_dur:.1f}s，不会出现")
    return out


def build_subs(spec, lines, seg_bounds, total_dur):
    """
    字幕构建 —— `spec["subs"]` 支持四种形态：

      · 省略 / "all"        → **全程字幕**（默认，兼容原有行为）
      · "none"              → **完全不上字幕**（画面只有卡片/序号条）
      · 数组                → **精选字幕**：只上指定的几句（推荐给"只上金句"）
      · {"keep": ["词",...]} → **关键词筛选**：只保留含这些词的字幕行

    精选字幕每一项：
      {"anchor": "某句话"}                     ← **最简：只写锚点，字幕照抄原句**
      {"anchor": "...", "text": "显示文本"}     ← 想改写上屏文字时给 text
      {"index": 3}                             ← 按第 3 行
      {"anchor": "...", "hold": 3.0}            ← 固定显示 3 秒（默认跟随那句话）
      {"anchor": "...", "marks": [...]}         ← 单条自定义标色（覆盖全片 marks）

    ⭐ 另外 `spec["subs_emph"]` 可给**指定的几句**叠加样式（与上面哪种模式都兼容），
       用于「全程字幕 + 金句突出」：把某几句换成「强调」样式，或单独改字号/颜色。
    """
    mode = spec.get("subs", "all")
    all_marks = spec.get("marks") or []

    def plain(rows):
        return [{"start": float(ln["start"]), "end": float(ln["end"]),
                 "text": ln["text"], "marks": all_marks} for ln in rows]

    if isinstance(mode, str) and mode.strip().lower() in ("none", "无", "关闭", "off"):
        print("    字幕策略：**不上字幕**（画面只保留卡片/序号条）")
        subs = []
    elif isinstance(mode, dict):                    # 关键词筛选
        keep = [str(k) for k in (mode.get("keep") or [])]
        keys = [_key(k) for k in keep if _key(k)]
        if not keys:
            print("    字幕策略：keep 为空 → 退化为全程字幕")
            subs = plain(lines)
        else:
            hit = [ln for ln in lines if any(k in _key(ln["text"]) for k in keys)]
            print(f"    字幕策略：关键词筛选 → 命中 {len(hit)}/{len(lines)} 行"
                  f"（保留词：{'、'.join(keep)}）")
            subs = plain(hit)
    elif isinstance(mode, list):                    # 精选字幕
        print(f"    字幕策略：**精选字幕**（只上 {len(mode)} 句，时长跟随原句）")
        subs = place_cards(mode, lines, seg_bounds, "精选字幕", 3.0, total_dur,
                           follow_anchor=True, fill_text=True,
                           base_marks=all_marks)
    else:                                           # 默认：全程
        print(f"    字幕策略：全程（{len(lines)} 行）")
        subs = plain(lines)

    return apply_subs_emph(subs, spec, lines, seg_bounds)


# 可从 subs_emph 透传到字幕项的样式键
_EMPH_KEYS = ("style", "size", "color", "bold", "scale", "outline",
              "shadow", "spacing", "outline_color", "anim")


def apply_subs_emph(subs, spec, lines, seg_bounds):
    """
    给**指定的几句**字幕叠加样式 —— 用于「全程字幕 + 金句突出」那种版本。

    ⚠️ 只对**已经出现在字幕列表里**的句子生效：
       精选模式下若某句没被选进 subs，这里的强调会跳过并提示（不会凭空造出字幕）。
    """
    emph = spec.get("subs_emph")
    if not emph or not subs:
        return subs
    items = emph if isinstance(emph, list) else [emph]
    n, missed = 0, []
    for it in items:
        if not isinstance(it, dict):
            continue
        _pos, err, src = resolve_place(it, lines, seg_bounds, 2.0)
        if src is None:
            missed.append((str(it.get("anchor") or it.get("index", "")), err))
            continue
        key = _key(src["text"])
        hit = next((s for s in subs if _key(s.get("text", "")) == key), None)
        if hit is None:
            missed.append((src["text"], "该句不在当前字幕列表里"
                                       "（精选模式下请先把它加进 subs）"))
            continue
        for k in _EMPH_KEYS:
            if it.get(k) is not None:
                hit[k] = it[k]
        n += 1
    if n:
        print(f"    → 已给 {n} 句字幕叠加强调样式")
    for txt, err in missed:
        print(f"    ⚠️ 强调句「{str(txt)[:16]}」未生效：{err}")
    return subs


# ---------------- 主流程 ----------------
def make(spec: dict, workdir: str):
    os.makedirs(workdir, exist_ok=True)
    print("=" * 70)
    _in = spec.get("videos") or ([spec["video"]] if spec.get("video") else [])
    print(f"素材：{len(_in)} 个文件" if len(_in) > 1 else f"素材：{_in[0] if _in else '?'}")
    if len(_in) > 1:
        for i, f in enumerate(_in):
            print(f"       {i+1}. {os.path.basename(f)}")
    print(f"输出：{spec['out']}")
    print("=" * 70)

    # 输入素材：1 个（单文件）或 N 个（分段拍 → 每个文件算一段）
    # ⭐ 多文件是**最可靠**的分段方式：不用猜、不受底噪影响、段序可控。
    videos = list(spec.get("videos") or ([spec["video"]] if spec.get("video") else []))
    if not videos:
        raise SystemExit("请提供素材：--video 素材.mp4（可给多个，空格分隔）")
    multi = len(videos) > 1
    vcfg = spec.get("visual") or {}
    visual_on = vcfg.get("enabled", True)
    crf = spec.get("crf", 18)
    preset = spec.get("preset", "medium")
    so = list(spec.get("silence_opts") or [0.35, 0.8])
    while len(so) < 2:
        so.append([0.35, 0.8][len(so)])

    # 阶段编号自动生成——两种模式（1 个文件 / N 个文件）都不跳号
    _st = [0]

    def stage(title: str):
        _st[0] += 1
        print(f"\n{'①②③④⑤⑥⑦⑧⑨'[_st[0] - 1]} {title}")

    seg_bounds = []          # 各段在最终时间轴上的起止（供卡片的 seg 锚点定位）
    pending_bounds = None

    # 素材规整
    #    多文件：按文件分段 → 归一化尺寸/帧率 → 叠化串联 → 色温对齐
    #    单文件：剪停顿（**保留**段间长停顿，留给下一阶段按静音切段）
    stage1 = os.path.join(workdir, "_stage1_cut.mp4")
    video_for_cut = videos[0]
    keep = [(0.0, probe_duration(videos[0]))]
    if multi:
        import video_visual as vv
        stage(f"素材拼接（{len(videos)} 段 → 叠化 + 色温对齐 + 降噪）")
        for i, f in enumerate(videos):
            print(f"    {i + 1}. {os.path.basename(f)}  {vv.probe_duration(f):.2f}s")
        entries = vv.entries_from_files(videos, vcfg.get("trim_tail", 0.0))
        entries, merged = vv.merge_short_entries(entries)
        if merged:
            print(f"    ⚠️ {merged} 个片段过短（< {vv.MIN_SEG}s），已并入相邻段")
        fps_u = vv.plan_uniform_fps(entries)
        w_u, h_u = vv.plan_uniform_size(entries)
        if fps_u:
            print(f"    帧率不一致 → 统一到 {fps_u:g}fps")
        if w_u:
            print(f"    分辨率不一致 → 统一到 {w_u}x{h_u}")
        cm = vcfg.get("color_match", True)
        gains = None
        if visual_on and cm and len(entries) > 1:
            gains = vv.compute_gains(vv.measure_entries_colors(entries))
            print("    色温对齐增益：" + " ".join(
                f"({g[0]:.3f},{g[1]:.3f},{g[2]:.3f})" for g in gains))
        dn_name = vcfg.get("denoise", "关闭")
        dn = vv.DENOISE_PRESETS.get(dn_name) if visual_on else None
        xd = vcfg.get("xfade", 0.25) if visual_on else 0.0
        trans = vcfg.get("transition", "叠化") if visual_on else "无"
        lens = [e["end"] - e["start"] for e in entries]
        pending_bounds = seg_bounds_of(lens, xd)
        joined = os.path.join(workdir, "_stage0_join.mp4")
        vv.build_timeline(entries, joined, gains, xd, trans, dn,
                          visual_on and cm, crf, preset, w_u, h_u, fps_u)
        print(f"    → {os.path.basename(joined)}  {vv.probe_duration(joined):.2f}s"
              + (f"（叠化 {xd}s × {len(entries) - 1}）" if xd else "（硬切）")
              + (f"  降噪 {dn_name}" if dn else ""))
        video_for_cut = joined
        preserve = None          # 已拼接，段间停顿不再需要保留
    else:
        # ⚠️ 段间叠化要在剪停顿时**保留**段间长停顿，否则切不出段
        preserve = vcfg.get("seg_gap", 1.2) if visual_on else None

    stage("剪停顿")
    # ⚠️ BGM=「头尾」时**必须保留头尾静音**——那块静音就是 BGM 的落点。
    #    否则剪停停顿一下（压到 0.35s），后面 BGM 计划就会报「头尾太短」。
    #    这里只看配置字面值，不需要等 ASR（计划在剪辑之后才算）。
    _bgm_raw = spec.get("bgm")
    _bgm_place = ""
    if isinstance(_bgm_raw, dict):
        _bgm_place = str(_bgm_raw.get("placement") or "").lower()
    keep_edges = bool(_bgm_raw) and _bgm_place not in ("full", "全程", "全片", "整片")
    if spec.get("cut_silence", True):
        _, keep = cut_silence(video_for_cut, stage1, so[0], so[1], preserve, keep_edges)
    else:
        print("    跳过（spec.cut_silence = false）")
        shutil.copy(video_for_cut, stage1)
        keep = [(0.0, probe_duration(stage1))]

    # ⚠️ 多文件模式的段边界是在「拼接时间轴」上算的，剪停顿后会变短，
    #    必须换算到新时间轴，否则卡片用 seg 锚点会整体偏移。
    if pending_bounds:
        seg_bounds = [(map_time(s, keep), map_time(e, keep)) for s, e in pending_bounds]

    # 画面处理：段间叠化 + 色温对齐 + 降噪
    # ⚠️ 本步会**改变时间轴总长**（每个转场吃掉 xfade 秒），
    #    所以必须在语音识别之前完成，否则字幕时间码会整体错位。
    stage2 = stage1
    if multi:
        if not visual_on:
            print("\n（画面处理已关闭，多文件仅做硬切拼接）")
    elif visual_on:
        import video_visual as vv
        stage("画面处理（段间叠化 / 色温对齐 / 降噪）")
        seg_gap = vcfg.get("seg_gap", 1.2)
        noise_db = vcfg.get("noise_db", -35.0)
        segs, gaps = vv.find_segments(stage1, seg_gap, noise_db)
        dn_name = vcfg.get("denoise", "关闭")
        dn = vv.DENOISE_PRESETS.get(dn_name)
        cm = vcfg.get("color_match", True)
        xd = vcfg.get("xfade", 0.25)
        trans = vcfg.get("transition", "叠化")
        gains = None
        if len(segs) > 1:
            print(f"    切出 {len(segs)} 段、段间停顿 {len(gaps)} 处"
                  f" → 叠化 {xd}s × {len(segs) - 1}")
            if cm:
                gains = vv.compute_gains(vv.measure_segment_colors(stage1, segs))
                print("    色温对齐增益：" + " ".join(
                    f"({g[0]:.3f},{g[1]:.3f},{g[2]:.3f})" for g in gains))
        else:
            print("    未检测到段间长停顿，只有 1 段（不做叠化）")
            for t in vv.health_check(1, vv.probe_duration(stage1), "single"):
                print(f"    {t}")
        if len(segs) > 1 or dn:
            if dn:
                print(f"    画面降噪：{dn_name}  {dn}")
            stage2 = os.path.join(workdir, "_stage2_visual.mp4")
            vv.xfade_segments(stage1, stage2, segs, gains, xd, trans, dn, cm,
                              crf, preset)
            print(f"    → {os.path.basename(stage2)}  {vv.probe_duration(stage2):.2f}s")
            if len(segs) > 1:
                seg_bounds = seg_bounds_of([e - s for s, e in segs], xd)
        else:
            print("    无需画面处理，跳过")
    else:
        print("\n（画面处理已关闭：spec.visual.enabled = false）")

    # ③ ASR —— 必须跑在画面处理之后，时间码才与最终时间轴一致
    stage("语音识别取时间码")
    timings_path = os.path.join(workdir, "timings.json")
    lines = spec.get("lines")
    if not lines:
        import video_asr
        if spec.get("script"):
            # 有已知文案 -> 只取时间码，文字用已知的那份（更准）
            raw_lines = video_asr.load_script(spec["script"])
            print(f"    已知文案 {len(raw_lines)} 行，只从 ASR 取时间码")
            words = video_asr.transcribe(stage2, spec.get("model", "small"), "zh")
            lines = video_asr.align_lines_to_words(raw_lines, words)
        else:
            # 无文案 -> 直接用 ASR 分段（听写模式）
            print("    未提供文案，使用 ASR 分段直接作字幕")
            lines = video_asr.transcribe_segments(stage2, spec.get("model", "small"), "zh")
        with open(timings_path, "w", encoding="utf-8") as f:
            json.dump({"lines": lines}, f, ensure_ascii=False, indent=1)
    else:
        print(f"    使用剪辑单内预置时间码（{len(lines)} 行），跳过模型")

    # 生成 ASS —— 位置用「锚点」表达，**不必写秒数**
    stage("生成 ASS 字幕")
    if not lines:
        print("    ⚠️ 未取得任何字幕行（素材里可能没有人声）")
    _total = probe_duration(stage2)
    subs = build_subs(spec, lines, seg_bounds, _total)
    seq = place_cards(spec.get("seq"), lines, seg_bounds, "序号条", 2.5, _total)

    # 开头大字钩子（静音场景靠它抓人）+ 金句卡，一起走重叠保护
    punch_raw = []
    hook = spec.get("hook")
    if hook:
        h = dict(hook) if isinstance(hook, dict) else {"text": str(hook)}
        h.setdefault("start", 0.0)
        if h.get("end") is None:
            h["end"] = float(h.get("start", 0.0)) + float(h.get("hold", 2.5))
        h.setdefault("style", "金句")
        # ⭐ 钩子**不加淡入**：视频号封面默认取视频第一帧，
        #    带 \fad 的话第一帧是完全透明的 → 封面会变成"纯画面无文字"
        h.setdefault("anim", "")
        punch_raw.append(h)
        print(f"    开头钩子：「{str(h['text'])[:18]}」"
              f"{h['start']:.1f}~{h['end']:.1f}s（无淡入，保证第一帧可做封面）")
    if spec.get("punch"):
        _p = spec["punch"]
        punch_raw += (_p if isinstance(_p, list) else [_p])
    # 浅底文字卡（台词小卡 / 话术卡 / 小字卡 / 祝愿卡）—— 与金句卡走**同一套重叠保护**：
    # 它们都落在画面中下部，互相压住同样是"文字叠字"。这里统一交给 place_cards。
    for _c in (spec.get("cards") or []):
        if isinstance(_c, dict):
            _c = dict(_c)
            _c.setdefault("style", "小卡")
            _c.setdefault("hold", 3.0)      # MD 里常写"停 3 秒"
            punch_raw.append(_c)
    punch = place_cards(punch_raw, lines, seg_bounds, "金句卡", 4.5, _total)

    ass_path = os.path.join(workdir, "subs.ass")
    build_ass({"subs": subs, "seq": seq, "punch": punch}, ass_path)
    # 细分计数：hook / 金句卡 / 浅底卡 都走 punch 通道，但打印时要能分开核对
    _n_hook = 1 if spec.get("hook") else 0
    _n_small = sum(1 for x in punch if (x.get("style") or "") in ("小卡", "引用"))
    _n_punch = len(punch) - _n_hook - _n_small
    print(f"    → 字幕 {len(subs)} 行 / 序号条 {len(seq)}"
          f" / 开头钩子 {_n_hook} / 金句卡 {_n_punch} / 浅底卡 {_n_small}"
          + (f" / 画面推近 {float(spec.get('zoom') or 0):.2f}"
             if spec.get("zoom") else ""))
    for _i in safe_check({"subs": subs, "seq": seq, "punch": punch}):
        print(f"    ⚠️ 安全区：{_i}")
    if seg_bounds:
        print("    段边界（seg 锚点可引用）：" + "  ".join(
            f"{i + 1}段@{s:.1f}s" for i, (s, _) in enumerate(seg_bounds)))

    # ---- BGM 计划（**默认不启用**；MD / 剪辑单显式给了才混）----
    # ⭐ 位置是参数：placement = "head_tail"（默认，只垫头尾无口播处）/ "full"（全程垫底 + ducking）
    bgm_plan = None
    bgm_cfg = spec.get("bgm")
    if bgm_cfg:
        import video_bgm as vb
        if isinstance(bgm_cfg, str):        # 简写：给个文件名或风格词即可
            low = bgm_cfg.lower()
            bgm_cfg = ({"file": bgm_cfg} if low.endswith(vb.AUDIO_EXTS)
                       else {"style": bgm_cfg})
        hints = [os.path.dirname(os.path.abspath(spec["out"]))] if spec.get("out") else []
        if videos:
            hints.append(os.path.dirname(os.path.abspath(videos[0])))
        dirs = vb.bgm_dirs(*hints)
        extra = os.path.dirname(os.path.abspath(videos[0])) if videos else None
        try:
            bgm_plan = vb.plan(bgm_cfg, lines, probe_duration(stage2), dirs, extra)
        except ValueError as e:
            print("\n" + "!" * 70)
            print("⛔ BGM 无法启用，已停下")
            print("   （不会产出「你以为垫了 BGM、其实没有」的成片）")
            print(f"   {e}")
            print("!" * 70)
            sys.exit(2)
        if bgm_plan.get("skip"):
            print(f"\n【BGM】已关闭（{bgm_plan.get('reason')}）")
            bgm_plan = None
        else:
            print("\n【BGM】")
            for _l in vb.describe(bgm_plan):
                print(f"    {_l}")

    # 音频处理
    stage("音频处理链")
    audio_chain, audio_cwd, ext_audio = None, None, None
    acfg_in = spec.get("audio") or {}
    audio_on = acfg_in.get("enabled", True)
    dur = probe_duration(stage2)

    if bgm_plan and not audio_on:
        print("\n" + "!" * 70)
        print("⛔ 冲突：启用了 BGM，但 audio.enabled = false")
        print("   BGM 的混音与响度标准化都要走音频处理链（否则响度不受控），二者不能只开一个。")
        print("   → 要么去掉 bgm，要么把 audio.enabled 设为 true。")
        print("!" * 70)
        sys.exit(2)

    if audio_on:
        import video_audio as va
        preset_name = acfg_in.get("preset", "标准")
        cfg = va.config_from_spec(acfg_in)
        ov = va.overrides_from_spec(acfg_in)
        print(f"    预设：{preset_name}" + (f"（另覆盖 {len(ov)} 项）" if ov else ""))
        # 先干净地编译一次前置链，用它去测量（loudnorm 两遍法必须测"被处理过"的信号）
        pre, chain_cwd = va.build_chain(cfg)
        # arnndn 的模型必须以文件名出现 → 复制到 workdir，让 workdir 同时容纳 ass 与 rnnn
        if chain_cwd:
            model = cfg.get("arnndn", {}).get("model", "bd.rnnn")
            src_model = os.path.join(chain_cwd, os.path.basename(model))
            if os.path.exists(src_model):
                shutil.copy(src_model, os.path.join(workdir, os.path.basename(model)))

        two_pass = bool(cfg.get("loudnorm", {}).get("enabled")
                        and cfg["loudnorm"].get("two_pass", True))
        if bgm_plan:
            # ⭐ Stage A：前置链 + BGM → WAV（混音**必须**在 loudnorm 之前，见 mix_bgm 说明）
            mix = os.path.join(workdir, "_bgm_mix.wav")
            mix_bgm(stage2, bgm_plan, pre, workdir, mix, dur)
            ext_audio = mix
            # 测量「混音后」的信号（不是混音前的口播，否则响度补偿会算错）
            measured = va.analyze(mix) if two_pass else None
            audio_chain = ",".join(x for x in (va.build_loudnorm(cfg, measured),
                                               va.build_post(cfg, dur)) if x)
            print(f"    混音后处理链：{audio_chain}")
        else:
            measured = va.analyze(stage2, pre, chain_cwd) if two_pass else None
            audio_chain, _ = va.build_full_chain(cfg, measured, dur)
            print(f"    {audio_chain}")
        audio_cwd = workdir
    else:
        print("    未启用（spec.audio.enabled = false）")

    stage("烧字幕并合成")
    compose(stage2, ass_path, spec["out"], audio_chain, audio_cwd,
            spec.get("crf", 18), spec.get("preset", "medium"), spec.get("bitrate"),
            ext_audio=ext_audio, zoom=spec.get("zoom", 0.0))

    # 封面（at 支持 "end" / 秒数 / anchor 文本）
    cover = None
    cover_cfg = spec.get("cover") or {}
    if cover_cfg:
        stage("封面")
        at = cover_cfg.get("at", 0.0)
        if at == "end":
            at = max(0.0, probe_duration(stage2) - 2.0)
        elif cover_cfg.get("anchor"):
            pos, err = resolve_place(cover_cfg, lines, seg_bounds, 2.0)
            if pos is None:
                print(f"    ⚠️ 封面锚点定位失败（{err}），改用片头帧")
                at = 0.0
            else:
                at = pos[0]
        cover = make_cover({**spec, "video": stage2}, workdir,
                           os.path.join(workdir, "cover.png"), at=float(at))

    print("\n" + "=" * 70)
    print("完成")
    print("=" * 70)
    _sz = os.path.getsize(spec["out"])
    _dur = probe_duration(spec["out"])
    _mbps = _sz * 8 / max(_dur, 0.1) / 1e6
    print(f"  成片：{spec['out']}  ({_sz / 1024 / 1024:.1f} MB)")
    print(f"  时长：{_dur:.2f}s   总码率：{_mbps:.1f} Mbps（含音频）")
    if _mbps < 6:
        print("     ⚠️ 低于视频号建议的 6~10 Mbps —— 平台二次压缩后画质会更糊；"
              "可用 --bitrate 8M 提高")
    if cover:
        for c in cover:
            print(f"  封面：{c}")
    return spec["out"]


# ---------------- 默认参数（全部可被 CLI / --set 覆盖） ----------------
def default_spec() -> dict:
    """标准能力：不传任何参数时的默认行为。已实测可用，参数待用真实口播素材微调。"""
    return {
        "cut_silence": True,          # 剪掉过长停顿
        "model": "small",             # 语音识别模型（可用 local path）
        "visual": {                   # 画面处理
            "enabled": True,
            "seg_gap": 1.2,           # 单文件模式：静音 ≥ 此秒数即视为「段间停顿」→ 切段并叠化
            "noise_db": -35.0,        # 单文件模式：静音判定阈值；有底噪/混响时用 -25 ~ -30
            "trim_tail": 0.0,         # 多文件模式：裁掉每段尾部静音（秒），0=不裁
            "transition": "叠化",      # 叠化/黑场/白场/溶解/左滑/上滑/无
            "xfade": 0.25,            # 转场时长（秒）；0 = 硬切
            "color_match": True,      # 段间色温/亮度对齐
            "denoise": "关闭",         # 画面降噪：关闭/轻/中/强（正片建议「轻」）
        },
        "audio": {"enabled": True, "preset": "标准", "override": {}},
        # 字幕策略：
        #   "all"（默认，全程） / "none"（不上字幕）
        #   [ {anchor:"某句"}, ... ]  精选字幕（只上这几句，时长跟随原句）
        #   {"keep": ["词1","词2"]}    关键词筛选
        "subs": "all",
        # 给指定的几句字幕叠加样式（与上面哪种模式都兼容）——「全字幕 + 金句突出」
        #   [{"anchor": "某句话", "style": "强调"}]
        #   [{"anchor": "某句话", "size": 86, "color": "#C2703C", "bold": true}]
        "subs_emph": None,
        "marks": [],                  # 全片通用标色规则 [{word,color,bold,scale}]
        # 卡片类：位置用「锚点」表达，不必写秒数（见 SKILL.md「位置怎么给」）
        #   anchor: "文本"  → 自动定位到含该文本的那句字幕
        #   at:     "end" | 秒数
        "punch": None,                # 金句大字卡 {text,marks,anchor|at,hold}
        "cover": None,                # 封面 {text,at}
        "crf": 18,                    # 画质（越小越好越大文件）
        "preset": "medium",           # x264 速度档
        "bitrate": None,              # 目标码率（如 "8M"）；None = CRF 模式
        # 画面轻微推近（Ken Burns）：整片从 1.0 缓慢推到 1+zoom。
        #   0 = 关（默认）。常用 0.05~0.08（"轻微"）—— 太大就显得刻意。
        # ⚠️ 会明显拖慢编码（每帧重采样），只在需要时开。
        "zoom": 0.0,

        # 开头大字钩子 —— 视频号/朋友圈是**静音自动播放**，前 3 秒靠大字抓人。
        #   {"text": "他是不是装的？", "hold": 2.5, "marks": [...]}
        # ⭐ 钩子**不加淡入**（代码里已处理）：视频号封面默认取第一帧，
        #    带淡入会让第一帧变成"纯画面无文字"。
        "hook": None,

        # ---- BGM（背景音乐）——⭐ **默认不启用** ----
        #   默认值判据：**需要「额外素材」的项默认关**（punch / cover / hook / bgm），
        #               **对「已有素材」做处理的项默认开**（audio / visual / cut_silence）。
        #   {
        #     "file": "轻音乐.mp3",        # 或 "style": "安静的钢琴"（按风格从曲库筛）
        #     "placement": "头尾",          # ⭐ 参数：头尾（默认）/ 全程（会自动 ducking 压低）
        #     "gain": -24,                 # 相对口播的音量（dB）
        #     "duck": 12,                  # 仅「全程」用：人声出现时压低多少 dB
        #     "fade_in": 1.0, "fade_out": 2.0,
        #     "dips": [{"anchor": "某句", "extra": 6, "hold": 0.5}]   # 定点额外压低
        #   }
        # ⛔ 找不到曲子 / 头尾没人声可垫 → **报错停下**，绝不静默产出"没 BGM 的成片"
        "bgm": None,
    }


def parse_value(s: str):
    """把命令行字符串解析成合适类型：bool / int / float / JSON / str"""
    low = s.strip().lower()
    if low in ("true", "false"):
        return low == "true"
    if low in ("null", "none"):
        return None
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    if s.strip()[:1] in ("[", "{"):
        try:
            return json.loads(s)
        except Exception:
            pass
    return s


def set_by_path(d: dict, dotted: str, value) -> None:
    """
    按点号路径写入嵌套 dict。中间层不存在会自动创建。
    例：set_by_path(spec, "audio.arnndn.mix", 0.9)
    """
    keys = dotted.split(".")
    cur = d
    for k in keys[:-1]:
        if not isinstance(cur.get(k), dict):
            cur[k] = {}
        cur = cur[k]
    cur[keys[-1]] = value


def show_chain(spec: dict) -> None:
    """打印这条 spec 最终会用的 ffmpeg 滤镜链（不实际处理，方便 Agent 核对）"""
    import video_audio as va
    acfg = spec.get("audio", {})
    vcfg = spec.get("visual") or {}
    _vids = spec.get("videos") or ([spec["video"]] if spec.get("video") else [])
    _multi = len(_vids) > 1
    print("=" * 70)
    print("画面处理")
    print("=" * 70)
    if not vcfg.get("enabled", True):
        print("  （已关闭：多文件仅硬切拼接，单文件不做叠化）")
    elif _multi:
        print(f"  分段方式：多文件（{len(_vids)} 段，顺序即段序，无需静音推断）")
        print(f"  归一化：各段尺寸/帧率不一致时自动统一")
        print(f"  转场：{vcfg.get('transition')} {vcfg.get('xfade')}s × {len(_vids) - 1}"
              f"   色温对齐：{'开' if vcfg.get('color_match', True) else '关'}"
              f"   降噪：{vcfg.get('denoise', '关闭')}")
        if vcfg.get("trim_tail"):
            print(f"  每段尾部裁静音：{vcfg['trim_tail']}s")
    else:
        print(f"  分段方式：单文件按静音切段"
              f"（阈值 {vcfg.get('noise_db', -35.0):g}dB，段间 ≥ {vcfg.get('seg_gap', 1.2)}s）")
        print(f"  转场：{vcfg.get('transition')} {vcfg.get('xfade')}s"
              f"   色温对齐：{'开' if vcfg.get('color_match', True) else '关'}"
              f"   降噪：{vcfg.get('denoise', '关闭')}")
        print("  （实际切出几段要跑起来才知道；先用 video_visual.py --probe 探）")
    print()
    print("=" * 70)
    print("视频滤镜")
    print("=" * 70)
    print(f"  scale={OUT_W}:{OUT_H}:force_original_aspect_ratio=increase,"
          f"crop={OUT_W}:{OUT_H},ass=subs.ass")
    print()
    print("=" * 70)
    print("BGM（背景音乐）")
    print("=" * 70)
    bgm_cfg = spec.get("bgm")
    if not bgm_cfg:
        print("  （未启用 —— ⭐ 默认就不垫 BGM）")
    else:
        b = bgm_cfg if isinstance(bgm_cfg, dict) else {"file": bgm_cfg}
        src = (f'file = {b["file"]}' if b.get("file")
               else (f'style = {b["style"]}' if b.get("style")
                     else "（既没给 file 也没给 style）"))
        raw = str(b.get("placement") or "头尾")
        full = raw in ("全程", "全片", "full")
        print(f"  曲目：{src}")
        print(f"  位置：{'全程（整片垫底 + 自动压低）' if full else '头尾（只垫没有口播处）'}")
        print(f"  音量：{b.get('gain', -24)} dB 相对口播"
              + (f"，人声段再压 {b.get('duck', 12)} dB" if full else ""))
        print(f"  淡入/淡出：{b.get('fade_in', 1.0)}s / {b.get('fade_out', 2.0)}s")
        print("  （实际选到哪首、落在哪几段，要真跑才知道；"
              "曲库用 video_bgm.py --list 查）")
    print()
    print("=" * 70)
    print("音频滤镜")
    print("=" * 70)
    if not acfg.get("enabled", True):
        print("  （已关闭，音频原样保留）")
        return
    cfg = va.config_from_spec(acfg)
    pre, _ = va.build_chain(cfg)
    ln = va.build_loudnorm(cfg)
    post = va.build_post(cfg)
    for part in (pre, ln, post):
        if part:
            print(f"  {part}")
    print()
    print("  各环节开关：")
    for stage in ("highpass", "arnndn", "afftdn", "deesser", "compressor"):
        st = cfg.get(stage, {})
        on = st.get("enabled", False)
        print(f"    {stage:<12} {'开' if on else '关'}")
    eqn = len(cfg.get("eq") or [])
    print(f"    {'eq':<12} {eqn} 段")
    ln_on = cfg.get("loudnorm", {}).get("enabled", False)
    al_on = cfg.get("alimiter", {}).get("enabled", False)
    fd = cfg.get("fade", {})
    print(f"    {'loudnorm':<12} {'开' if ln_on else '关'}")
    print(f"    {'alimiter':<12} {'开' if al_on else '关'}")
    if fd.get("enabled"):
        print(f"    {'首尾淡入淡出':<8} 开（入 {fd.get('in_s')}s / 出 {fd.get('out_s')}s"
              f"，淡出起点按实际时长在运行时计算，故上方链中未显示）")
    else:
        print(f"    {'首尾淡入淡出':<8} 关")
    print()
    if ln_on:
        print(f"  目标响度 I    = {cfg['loudnorm'].get('I')} LUFS")
        print(f"  真峰值上限 TP = {cfg['loudnorm'].get('TP')} dBTP")
    else:
        print("  （响度标准化已关闭，不设响度目标）")


def list_presets() -> None:
    import video_audio as va
    print("可用音频预设（--audio-preset 或 spec.audio.preset）：")
    for name in va.PRESETS:
        print(f"  {name:<14} {va.describe_preset(name)}")
    print()
    print("可覆盖的参数路径（用 --set 或写进 spec.audio）：")
    for k, v in va.DEFAULT.items():
        if isinstance(v, dict):
            for k2 in v:
                print(f"  audio.{k}.{k2}")
        else:
            print(f"  audio.{k}")
    print()
    print("画面处理（写进 spec.visual，或用下方快捷开关）：")
    for k, v in default_spec()["visual"].items():
        print(f"  visual.{k}  (默认 {v!r})")
    print()
    print("其他可覆盖路径：")
    for k in ("cut_silence", "model", "crf", "preset", "bitrate", "zoom",
              "videos", "subs", "marks", "hook", "punch", "cards", "seq",
              "cover", "bgm"):
        print(f"  {k}")
    print()
    print("浅底文字卡（cards）—— 画面下方的浅底深字卡片，可有多张：")
    print('  [{"text": "我听到了，你现在很不想去", "anchor": "我听到了", "hold": 3.0}]')
    print('  样式：默认「小卡」（浅底深字）／可 "style":"引用"（更小+半透明+无动画）')
    print('  字号：写 "size": 82，或走 MD 的「比字幕大一号 / 小很多」')
    print()
    print("画面轻微推近（zoom）—— 整片从 1.0 缓推到 1+zoom（Ken Burns）：")
    print("  0 = 关（默认）；0.05~0.08 是「轻微」；⚠️ 每帧重采样，会明显拖慢编码")
    print()
    print("开头大字钩子（hook）—— 静音自动播放时靠它抓人，且保证第一帧可做封面：")
    print('  {"text": "他是不是装的？", "hold": 2.5}')
    print('  ⚠️ 钩子不加淡入；视频号封面默认取视频第一帧')
    print()
    print("BGM（背景音乐）—— ⭐ **默认不启用**，给了才混：")
    print('  --bgm-file 轻音乐.mp3             直接指定文件')
    print('  --bgm-style "安静的钢琴"           按风格从曲库筛（与上面二选一）')
    print('  --bgm-placement 头尾|全程           默认「头尾」＝只垫没有口播处；')
    print('                                     「全程」＝整片垫底 ＋ 人声出现时自动压低')
    print('  --bgm-gain -24                    音量（相对口播，dB）')
    print('  --bgm-duck 12                     仅「全程」：人声段压低多少 dB')
    print('  曲库位置：<本篇>/_素材/bgm/  或  <项目>/_资产/bgm/（配 曲库.md 标风格）')
    print('  查曲库：python video_bgm.py --list      试筛：--pick "安静的钢琴"')
    print()
    print("字幕策略（subs）—— 四种形态：")
    print('  "all"                       全程字幕（默认）')
    print('  "none"                      完全不上字幕（画面只留卡片/序号条）')
    print('  [{"anchor": "某句"}, ...]    精选字幕：只上这几句')
    print('                              （只写锚点即可，字幕照抄原句；时长跟随原句）')
    print('  {"keep": ["词1", "词2"]}     关键词筛选：只保留含这些词的字幕行')
    print()
    print("强调句（subs_emph）—— 给指定几句叠加样式，与上面任何模式兼容：")
    print('  [{"anchor": "某句", "style": "强调"}]        换成「强调」样式（更大更粗）')
    print('  [{"anchor": "某句", "size": 86, "color": "#C2703C", "bold": true}]')
    print('  可选样式名：字幕 / 强调 / 序号条 / 金句（金句=居中大字卡）')
    print()
    print("卡片位置怎么给（punch / seq / cover，优先级从上到下）：")
    print('  "anchor": "某句话"   推荐——自动定位到含该文本的字幕行，不写秒数')
    print('  "seg": 2             第 2 段开头（配 "offset" 微调）')
    print('  "at": "end"          片尾倒数若干秒（配 "hold"）')
    print('  "start": 12.5        硬写秒数（最不推荐，素材一变就错位）')
    print('  punch 与 cover 既可给单个对象，也可给数组（多张卡）')
    print()
    print("示例：")
    print("  --set audio.arnndn.mix=0.9 --set audio.loudnorm.I=-13")
    print("  --set visual.denoise=轻 --set visual.xfade=0.3")


# ---------------- 上屏方案预览（素材还没拍也能看） ----------------
def simulate_timings(script_lines, cps: float = 4.3, gap: float = 0.22):
    """
    按字数估算每句时长，拼出一份**模拟时间码**。

    ⚠️ 只用于预览上屏落点。真实成片的时间码一律以语音识别为准 ——
       这里看的是"各元素的**相对位置关系**对不对"（顺序、是否重叠、卡片挂对句），
       而不是绝对秒数。
    """
    out, t = [], 0.0
    for s in script_lines:
        n = len(re.sub(r"[^\w\u4e00-\u9fff]", "", s))
        dur = max(0.9, round(n / cps, 2))
        out.append({"text": s, "start": round(t, 2), "end": round(t + dur, 2),
                    "matched": True})
        t += dur + gap
    return out, round(t, 2)


def _ass_sec(x: str) -> float:
    h, m, rest = x.split(":")
    return int(h) * 3600 + int(m) * 60 + float(rest)


def preview_plan(spec, workdir) -> str | None:
    """
    只跑「文案 → 字幕/卡片」这一段：生成 ASS 并打印落点表。**不需要素材。**

    用途：MD 刚改完，先看落点对不对（哪句会出现、卡片挂没挂对、有没有挤在一起），
    确认无误再去拍 —— 省掉"拍完才发现上屏方案有问题"的返工。
    """
    script = spec.get("script")
    if not script or not os.path.exists(script):
        print("  ⚠️ 预览需要逐字稿：给 --script，或用 --md"
              "（会自动从 MD 抽出 `_文案.txt`）")
        return None
    raw = [s.strip() for s in open(script, encoding="utf-8") if s.strip()]
    if not raw:
        print(f"  ⚠️ 逐字稿是空的：{script}")
        return None

    lines, total = simulate_timings(raw)
    print("=" * 70)
    print("上屏方案预览（素材还没拍也能看）")
    print("=" * 70)
    print(f"  逐字稿 {len(raw)} 句，模拟总长 {total:.1f}s")
    print("  ⚠️ 模拟时间码按字数估算——**真实成片以语音识别为准**；"
          "这里看的是位置关系")

    subs = build_subs(spec, lines, [], total)
    punch = place_cards(spec.get("punch"), lines, [], "金句卡", 4.5, total)
    seq = place_cards(spec.get("seq"), lines, [], "序号条", 2.5, total)

    os.makedirs(workdir, exist_ok=True)
    ass = os.path.join(workdir, "preview.ass")
    build_ass({"subs": subs, "seq": seq, "punch": punch}, ass)

    # ⭐ 安全区检查（会不会被视频号 UI 压住）
    issues = safe_check({"subs": subs, "seq": seq, "punch": punch})
    if issues:
        print()
        print("  ⚠️ 安全区问题（可能被视频号 UI 压住）：")
        for i in issues:
            print(f"    · {i}")
    else:
        print("\n  ✅ 安全区检查通过（底部字幕已避开标题/评论区入口）")

    dlg = [ln for ln in open(ass, encoding="utf-8-sig").read().splitlines()
           if ln.startswith("Dialogue:")]
    print()
    for style in ("字幕", "强调", "序号条", "金句"):
        rows = [ln for ln in dlg if ln.split(",", 9)[3] == style]
        if not rows:
            continue
        print(f"  【{style}】{len(rows)} 条")
        for ln in rows:
            p = ln.split(",", 9)
            txt = re.sub(r"\{[^}]*\}", "", p[9]).replace("\\N", " / ")
            print(f"    {_ass_sec(p[1]):7.1f}s → {_ass_sec(p[2]):7.1f}s   {txt}")
    print()
    if not subs:
        print("  ℹ️ 本方案没有底部字幕（只有卡片/序号条）")
    print(f"  ASS：{ass}")

    # BGM 状态（preview 不校验素材，只看配置；实际选曲与落点要真跑）
    print()
    bgm_cfg = spec.get("bgm")
    if not bgm_cfg:
        print("  【BGM】未启用（⭐ 默认就不垫背景音乐）")
    else:
        b = bgm_cfg if isinstance(bgm_cfg, dict) else {"file": bgm_cfg}
        src = (f'曲目 {b["file"]}' if b.get("file")
               else (f'风格「{b["style"]}」' if b.get("style")
                     else "（未给曲目/风格 —— 会报错停下）"))
        raw = str(b.get("placement") or "头尾")
        full = raw in ("全程", "全片", "full")
        print(f"  【BGM】{src}｜位置："
              f"{'全程（人声段自动压低）' if full else '头尾（只垫无口播处）'}"
              f"｜音量 {b.get('gain', -24)}dB")
        print("     ⚠️ 能否找到曲子、头尾段够不够长，要真跑才知道")
    return ass


def main():
    ap = argparse.ArgumentParser(
        description="口播素材 → 带字幕的竖屏短视频（1080x1920），全程 ffmpeg，不依赖剪映",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # ⭐ 最省事：文案 MD + 素材目录（MD 里的「上屏方案」自动变成剪辑单）
  python video_make.py --md 文案.md --videos-dir _素材 --out 成片.mp4

  # 最少参数（走全部标准默认）
  python video_make.py --video 素材.mp4 --script 文案.txt --out 成片.mp4

  # 临时调参（不改任何文件）
  python video_make.py --video 素材.mp4 --script 文案.txt --out 成片.mp4 \\
      --set audio.arnndn.mix=0.9 --set audio.loudnorm.I=-13

  # 加背景音乐（⭐ 默认不垫；位置也是参数）
  python video_make.py --md 文案.md --videos-dir _素材 --out 成片.mp4 \\
      --bgm-style "安静的钢琴" --bgm-placement 头尾
  #   头尾 = 只垫没有口播的地方（默认）｜全程 = 整片垫底 + 人声段自动压低
  #   查曲库： python video_bgm.py --list

  # 看最终会用的参数 / 滤镜链 / 可用预设
  python video_make.py --dump-params
  python video_make.py --show-chain
  python video_make.py --list-presets
        """)
    ap.add_argument("--md", metavar="文案.md",
                    help="文案 MD：自动读其中「上屏方案」区块生成剪辑单，"
                         "并从「口播文案」段抽出逐字稿（格式见 reference/md_authoring_guide.md）")
    ap.add_argument("--videos-dir", metavar="目录",
                    help="素材目录：按文件名排序取全部视频文件（忽略 _ 开头的产物），顺序即段序")
    ap.add_argument("--spec", help="剪辑单 JSON（给了就以此为基础，其余 CLI 参数仍可覆盖）")
    ap.add_argument("--video", nargs="+", metavar="文件",
                    help="素材：1 个文件，或 N 个文件（分段拍，空格分隔，顺序即段序）")
    ap.add_argument("--script", help="文案 txt（一行一句）；不给则用 ASR 听写；--md 时自动抽")
    ap.add_argument("--out")
    ap.add_argument("--workdir", help="中间产物目录（默认 <成片目录>/_过程文件）")
    ap.add_argument("--set", action="append", default=[], metavar="K=V",
                    help="动态覆盖任意参数，可重复，如 audio.loudnorm.I=-13")
    ap.add_argument("--dump-params", action="store_true", help="打印最终生效参数后退出")
    ap.add_argument("--show-chain", action="store_true", help="打印 ffmpeg 滤镜链后退出")
    ap.add_argument("--preview", action="store_true",
                    help="⭐ 素材还没拍也能看：用逐字稿模拟时间码，打印字幕/卡片落点"
                         "并生成 ASS（不合成视频）")
    ap.add_argument("--safe-check", action="store_true",
                    help="检查字幕/卡片会不会被视频号 UI 压住（走 --preview 同一套流程）")
    ap.add_argument("--list-presets", action="store_true", help="列出预设与可覆盖参数")
    # 常用快捷开关（等价于 --set，但更省事）
    ap.add_argument("--audio-preset", help="音频预设名（关闭/轻/标准/强/仿剪映声音美化）")
    ap.add_argument("--model", help="语音识别模型（tiny/base/small/medium/large-v3 或本地路径）")
    ap.add_argument("--no-audio", action="store_true", help="关闭音频处理")
    ap.add_argument("--no-cut-silence", action="store_true", help="不剪停顿")
    ap.add_argument("--subs", choices=["all", "none"],
                    help="字幕策略：all 全程（默认）/ none 不上字幕"
                         "（精选字幕请用 --set subs='[{\"anchor\":\"某句\"}]'）")
    # 画面处理快捷开关
    ap.add_argument("--no-visual", action="store_true",
                    help="关闭画面处理（段间叠化 / 色温对齐 / 降噪）")
    ap.add_argument("--denoise", help="画面降噪：关闭/轻/中/强")
    ap.add_argument("--transition", help="段间转场：叠化/黑场/白场/溶解/左滑/上滑")
    ap.add_argument("--seg-gap", type=float, help="段间判定静音秒数，默认 1.2（仅单文件模式）")
    ap.add_argument("--noise-db", type=float,
                    help="静音判定阈值 dB，默认 -35（仅单文件模式）；有底噪/混响时用 -25~-30")
    ap.add_argument("--trim-tail", type=float,
                    help="多文件模式：裁掉每段尾部静音秒数，0=不裁")
    ap.add_argument("--xfade", type=float, help="转场时长秒，默认 0.25")
    ap.add_argument("--no-color-match", action="store_true", help="关闭段间色温对齐")
    ap.add_argument("--crf", type=int, help="画质，默认 18")
    ap.add_argument("--zoom", type=float, metavar="幅度",
                    help="画面轻微推近（Ken Burns）：整片缓慢推近，如 0.06 = 推到 1.06；"
                         "0 = 关闭（默认）。⚠️ 会明显拖慢编码")
    # ---- BGM（背景音乐）——默认不启用 ----
    ap.add_argument("--bgm-file", metavar="文件",
                    help="背景音乐文件（默认不启用 BGM；给了才混）")
    ap.add_argument("--bgm-style", metavar="风格",
                    help="按风格从曲库筛（如「安静的钢琴」）；与 --bgm-file 二选一")
    ap.add_argument("--bgm-placement", metavar="位置",
                    help="BGM 位置：头尾（默认，只垫无口播处）/ 全程（自动压低）")
    ap.add_argument("--bgm-gain", type=float, metavar="dB",
                    help="BGM 音量（相对口播，默认 -24）")
    ap.add_argument("--bgm-duck", type=float, metavar="dB",
                    help="仅「全程」：人声出现时压低多少 dB（默认 12）")
    ap.add_argument("--bitrate", metavar="码率",
                    help="目标码率（如 8M / 8000k）；给了就改用平均码率模式。"
                         "视频号会二次压缩，建议 6~10 Mbps")
    ap.add_argument("--preset-fast", action="store_true", help="用 veryfast 编码（快，体积大）")
    args = ap.parse_args()

    # 只看参数/滤镜链时（--dump-params / --show-chain），不校验素材与输出路径 ——
    # 素材还没拍好就先看解析结果是正常用法（文案 MD 里就是这么建议的）
    dry = bool(args.dump_params or args.show_chain or args.preview or args.safe_check)

    if args.list_presets:
        list_presets()
        return

    # ---------- 组装 spec ----------
    if args.spec:
        spec = json.loads(open(args.spec, encoding="utf-8-sig").read())
        base = default_spec()
        base.update(spec)            # 剪辑单优先，未提及的用默认
        spec = base
    else:
        if not dry and not ((args.video or args.videos_dir) and args.out):
            ap.error("需要 --spec，或同时给素材（--video / --videos-dir）与 --out（--script 可选）")
        spec = default_spec()

    # ---------- 文案 MD → 剪辑单片段（可被下面的 CLI 参数与 --set 覆盖） ----------
    if args.md:
        import md_spec
        md_part = md_spec.parse_md(args.md)
        meta = md_part.pop("_from_md", None)
        spec.update(md_part)
        if meta:
            c = meta["counts"]
            print(f"[md] {os.path.basename(args.md)}：版本「{meta['version']}」"
                  f"｜强调句 {c['强调句']}｜大字卡 {c['大字卡']}｜"
                  f"序号条 {c['序号条']}｜标色 {c['标色']}｜封面 {c['封面']}"
                  f"｜开头钩子 {c.get('开头钩子', 0)}"
                  f"｜浅底卡 {c.get('浅底卡', 0)}"
                  f"｜画面推近 {'是' if c.get('画面推近') else '否'}"
                  f"｜背景音乐 {c.get('背景音乐', 0)}")
        if not args.script:
            txt = md_spec.extract_script(args.md)
            if txt.strip():
                sp = os.path.splitext(os.path.abspath(args.md))[0] + "_文案.txt"
                with open(sp, "w", encoding="utf-8") as f:
                    f.write(txt + "\n")
                spec["script"] = sp
                print(f"[md] 逐字稿已抽出 → {os.path.basename(sp)}"
                      f"（{len(txt.replace(chr(10), ''))} 字）")
        # 没给 --out 时，输出默认落在 MD 同目录（命令行给的 --out 稍后会覆盖它）
        if not args.out and not spec.get("out"):
            stem = os.path.splitext(os.path.basename(args.md))[0]
            # 从文件名里取发布序号（`视频号文案_01_发布第1条_…` → 01），
            # 这样成片叫 `_成片_01.mp4`，和 `_素材/01.mp4`、目录名 `01_xxx` 对齐
            m = re.search(r"[_\-](\d{1,2})[_\-]", stem)
            tag = m.group(1) if m else stem[:20]
            spec["out"] = os.path.join(os.path.dirname(os.path.abspath(args.md)),
                                       f"_成片_{tag}.mp4")
            print(f"[out] 未指定 --out → 默认输出 {os.path.basename(spec['out'])}")

    # ---------- 素材目录模式（按文件名排序，顺序即段序） ----------
    if args.videos_dir:
        exts = (".mp4", ".mov", ".mkv", ".m4v", ".avi", ".webm")
        if not os.path.isdir(args.videos_dir):
            ap.error(f"--videos-dir 不是目录：{args.videos_dir}")
        cand = sorted(
            os.path.join(args.videos_dir, f)
            for f in os.listdir(args.videos_dir)
            if f.lower().endswith(exts) and not f.startswith(("_", "."))
        )
        if not cand:
            if dry:
                print(f"[素材] ⚠️ 目录里还没有视频文件（`_` 开头会被忽略）：{args.videos_dir}")
            else:
                ap.error(f"--videos-dir 里没找到视频文件：{args.videos_dir}\n"
                         f"  → 把这条的分段素材放进去，命名 01.mp4 02.mp4 03.mp4"
                         f"（**按文件名排序 = 段序**）；\n"
                         f"    以 _ 开头的文件会被自动忽略（那是成片等产物）。")
        spec.pop("video", None)
        spec["videos"] = cand
        if len(cand) == 1:
            spec["video"] = cand[0]
        print(f"[素材] {len(cand)} 个（顺序即段序）→ "
              + "，".join(os.path.basename(c) for c in cand))

    if args.video:
        spec.pop("video", None)
        spec["videos"] = args.video
        if len(args.video) == 1:
            spec["video"] = args.video[0]
    if args.out:
        spec["out"] = args.out
    if args.script:
        spec["script"] = args.script
    if not dry and (not (spec.get("videos") or spec.get("video")) or "out" not in spec):
        ap.error("缺少 video 或 out")

    # ---------- 快捷开关 ----------
    if args.audio_preset:
        spec.setdefault("audio", {})["preset"] = args.audio_preset
    if args.no_audio:
        spec.setdefault("audio", {})["enabled"] = False
    if args.no_cut_silence:
        spec["cut_silence"] = False
    if args.subs:
        spec["subs"] = args.subs

    # ---------- BGM（默认不启用，故只在显式给了参数时才建这份配置）----------
    if (args.bgm_file or args.bgm_style or args.bgm_placement
            or args.bgm_gain is not None or args.bgm_duck is not None):
        b = dict(spec.get("bgm") or {}) if isinstance(spec.get("bgm"), dict) else {}
        if args.bgm_file:
            b["file"] = args.bgm_file
            b.pop("style", None)
        if args.bgm_style:
            b["style"] = args.bgm_style
            b.pop("file", None)          # 二选一，避免"到底用了哪个"含糊
        if args.bgm_placement:
            b["placement"] = args.bgm_placement
        if args.bgm_gain is not None:
            b["gain"] = args.bgm_gain
        if args.bgm_duck is not None:
            b["duck"] = args.bgm_duck
        spec["bgm"] = b

    # ---------- 画面处理快捷开关 ----------
    if not isinstance(spec.get("visual"), dict):
        spec["visual"] = dict(default_spec()["visual"])
    vset = spec["visual"]
    if args.no_visual:
        vset["enabled"] = False
    if args.denoise:
        vset["denoise"] = args.denoise
    if args.transition:
        vset["transition"] = args.transition
    if args.seg_gap is not None:
        vset["seg_gap"] = args.seg_gap
    if args.noise_db is not None:
        vset["noise_db"] = args.noise_db
    if args.trim_tail is not None:
        vset["trim_tail"] = args.trim_tail
    if args.xfade is not None:
        vset["xfade"] = args.xfade
    if args.no_color_match:
        vset["color_match"] = False

    if args.model:
        spec["model"] = args.model
    if args.crf:
        spec["crf"] = args.crf
    if args.zoom is not None:
        spec["zoom"] = args.zoom
    if args.preset_fast:
        spec["preset"] = "veryfast"

    # ---------- --set 动态覆盖（最后应用，优先级最高） ----------
    for kv in args.set:
        k, sep, v = kv.partition("=")
        if not sep:
            ap.error(f"--set 需要 K=V 形式，收到：{kv}")
        set_by_path(spec, k.strip(), parse_value(v))

    # ---------- 只查看 ----------
    if args.dump_params:
        print(json.dumps(spec, ensure_ascii=False, indent=1))
        return
    if args.show_chain:
        show_chain(spec)
        return

    if args.preview or args.safe_check:
        out = spec.get("out")
        base = os.path.dirname(os.path.abspath(out)) if out else os.getcwd()
        preview_plan(spec, args.workdir or os.path.join(base, "_过程文件"))
        return

    workdir = args.workdir or os.path.join(
        os.path.dirname(os.path.abspath(spec["out"])), "_过程文件")
    make(spec, workdir)


if __name__ == "__main__":
    main()
