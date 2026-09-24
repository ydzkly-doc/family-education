# -*- coding: utf-8 -*-
r"""
视频合成主控 —— 把「素材 + 文案 + 剪辑单」变成成片（全程不依赖剪映）

流水线：
  ① 剪停顿（silencedetect 找出长静音 → trim/concat 掐掉，保留自然停顿）
  ② ASR 取时间码（video_asr）
  ③ 生成 ASS 字幕（video_build_ass：全程字幕 / 序号条 / 金句大字卡）
  ④ ffmpeg 烧字幕 + 缩放裁切到 1080x1920
  ⑤ 出封面图

关键工程注意（都踩过）：
  · ffmpeg 滤镜参数用 ':' 分隔，Windows 路径 'C:\' 会被吃坏
    → 一律把 cwd 切到目标文件所在目录、只传文件名
  · 用 subprocess 传 list，不经过 shell（中文路径 + 特殊字符才安全）
  · 字幕必须自动折行，否则 CJK 满宽字符会溢出画面被裁

用法：
  python video_make.py --spec <剪辑单.json>
  python video_make.py --video <素材> --script <文案.txt> --out <成片.mp4> [--punch 文本] [...]

剪辑单 JSON 见 build_spec_example()
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
from video_build_ass import build_ass, WARM, WARM_DEEP, PLAY_RES_X, PLAY_RES_Y  # noqa: E402

FFMPEG = r"C:\Users\ZhuanZ\.workbuddy\binaries\ffmpeg\bin\ffmpeg.exe"
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
                         min_cut: float = 0.8):
    """
    把长静音压缩到 keep_gap 秒；短静音原样保留（那是自然停顿）。
    返回 [(start, end), ...]
    """
    cuts = []
    for s, e in silences:
        e = duration if e is None else e
        length = e - s
        if length <= min_cut:
            continue
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


def cut_silence(video: str, out_path: str, keep_gap=0.35, min_cut=0.8):
    dur = probe_duration(video)
    sil = detect_silences(video)
    keep = build_keep_intervals(dur, sil, keep_gap, min_cut)
    print(f"    原长 {dur:.2f}s，检出静音 {len(sil)} 段，保留 {len(keep)} 段")

    if len(keep) == 1 and abs(keep[0][1] - dur) < 0.05:
        print("    无需剪切，直接复用原素材")
        shutil.copy(video, out_path)
        return out_path

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
    return out_path


def probe_duration(video: str) -> float:
    p = subprocess.run([FFMPEG, "-hide_banner", "-i", video],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", p.stderr or "")
    if not m:
        raise RuntimeError("无法读取素材时长")
    h, mi, s = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(s)


# ---------------- ④ 合成 ----------------
def compose(video: str, ass_path: str, out_path: str, audio_chain: str | None = None,
            cwd: str | None = None, crf=18, preset="medium"):
    """
    缩放裁切到 1080x1920 + 烧 ASS 字幕 +（可选）音频处理链。

    cwd 说明：ass 与 arnndn 的 .rnnn 模型都必须以「文件名」形式出现在滤镜里，
    否则 Windows 盘符的冒号会破坏滤镜参数解析。故调用方需保证两者都在 cwd 下。
    """
    ass_name = os.path.basename(ass_path)
    work = cwd or os.path.dirname(os.path.abspath(ass_path))
    # 把 ass 放到 cwd（若已在则跳过）
    if os.path.dirname(os.path.abspath(ass_path)) != os.path.abspath(work):
        shutil.copy(ass_path, os.path.join(work, ass_name))

    vf = (f"scale={OUT_W}:{OUT_H}:force_original_aspect_ratio=increase,"
          f"crop={OUT_W}:{OUT_H},ass={ass_name}")
    args = [FFMPEG, "-hide_banner", "-y", "-i", os.path.abspath(video), "-vf", vf]
    if audio_chain:
        args += ["-af", audio_chain]
    args += ["-c:v", "libx264", "-preset", preset, "-crf", str(crf),
             "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
             os.path.abspath(out_path)]
    run(args, cwd=work, label=f"合成 -> {os.path.basename(out_path)}")
    return out_path


# ---------------- ⑤ 封面 ----------------
def make_cover(spec: dict, ass_dir: str, out_png: str, at: float = 0.0):
    cover = spec.get("cover")
    if not cover:
        return None
    cspec = {"punch": [{"start": 0.0, "end": 2.0,
                        "text": cover["text"],
                        "marks": cover.get("marks")}]}
    cpath = os.path.join(ass_dir, "_cover.ass")
    build_ass(cspec, cpath, wrap=True)
    src = spec.get("video")
    run([FFMPEG, "-hide_banner", "-y", "-ss", f"{at:.2f}", "-i", os.path.abspath(src),
         "-vf", f"scale={OUT_W}:{OUT_H}:force_original_aspect_ratio=increase,"
                f"crop={OUT_W}:{OUT_H},ass={os.path.basename(cpath)}",
         "-frames:v", "1", os.path.abspath(out_png)],
        cwd=ass_dir, label=f"封面 -> {os.path.basename(out_png)}")
    return out_png


# ---------------- 主流程 ----------------
def make(spec: dict, workdir: str):
    os.makedirs(workdir, exist_ok=True)
    video = spec["video"]
    print("=" * 70)
    print(f"素材：{video}")
    print(f"输出：{spec['out']}")
    print("=" * 70)

    # ① 剪停顿
    stage1 = os.path.join(workdir, "_stage1_cut.mp4")
    if spec.get("cut_silence", True):
        print("\n① 剪停顿")
        cut_silence(video, stage1, *spec.get("silence_opts", [0.35, 0.8]))
    else:
        print("\n① 剪停顿：跳过")
        shutil.copy(video, stage1)

    # ② ASR
    print("\n② 语音识别取时间码")
    timings_path = os.path.join(workdir, "timings.json")
    lines = spec.get("lines")
    if not lines:
        import video_asr
        if spec.get("script"):
            # 有已知文案 -> 只取时间码，文字用已知的那份（更准）
            raw_lines = video_asr.load_script(spec["script"])
            print(f"    已知文案 {len(raw_lines)} 行，只从 ASR 取时间码")
            words = video_asr.transcribe(stage1, spec.get("model", "small"), "zh")
            lines = video_asr.align_lines_to_words(raw_lines, words)
        else:
            # 无文案 -> 直接用 ASR 分段（听写模式）
            print("    未提供文案，使用 ASR 分段直接作字幕")
            lines = video_asr.transcribe_segments(stage1, spec.get("model", "small"), "zh")
        with open(timings_path, "w", encoding="utf-8") as f:
            json.dump({"lines": lines}, f, ensure_ascii=False, indent=1)
    else:
        print(f"    使用剪辑单内预置时间码（{len(lines)} 行），跳过模型")

    # ③ 构建 ASS
    print("\n③ 生成 ASS 字幕")
    subs = []
    for ln in lines:
        subs.append({"start": ln["start"], "end": ln["end"],
                     "text": ln["text"], "marks": spec.get("marks")})
    # 序号条：均匀铺在"得看三件事"之后，或按剪辑单给的时间
    seq = []
    for item in spec.get("seq", []):
        if "start" in item:
            seq.append(item)
    # 金句卡
    punch = []
    if spec.get("punch"):
        p = dict(spec["punch"])
        if p.get("at") == "end" or "start" not in p:
            last = lines[-1]
            p["start"] = max(0.0, float(last["end"]) - 4.0)
            p["end"] = float(last["end"]) + 2.5
        punch.append(p)

    ass_path = os.path.join(workdir, "subs.ass")
    build_ass({"subs": subs, "seq": seq, "punch": punch}, ass_path)
    print(f"    字幕 {len(subs)} 行 / 序号条 {len(seq)} / 金句卡 {len(punch)}")

    # ④ 合成
    print("\n④ 音频处理链")
    audio_chain, audio_cwd = None, None
    acfg_in = spec.get("audio", {})
    if acfg_in.get("enabled", True):
        import video_audio as va
        preset_name = acfg_in.get("preset", "标准")
        cfg = va.resolve(preset_name)
        if acfg_in.get("override"):
            cfg = va.merge(cfg, acfg_in["override"])
        print(f"    预设：{preset_name}")
        # 先干净地编译一次前置链，用它去测量（loudnorm 两遍法必须测"被处理过"的信号）
        pre, chain_cwd = va.build_chain(cfg)
        measured = None
        if (cfg.get("loudnorm", {}).get("enabled")
                and cfg["loudnorm"].get("two_pass", True)):
            measured = va.analyze(stage1, pre, chain_cwd)
        audio_chain, chain_cwd = va.build_full_chain(cfg, measured)
        print(f"    {audio_chain}")
        # arnndn 的模型必须以文件名出现 → 复制到 workdir，让 workdir 同时容纳 ass 与 rnnn
        if chain_cwd:
            model = cfg.get("arnndn", {}).get("model", "bd.rnnn")
            src_model = os.path.join(chain_cwd, os.path.basename(model))
            if os.path.exists(src_model):
                shutil.copy(src_model, os.path.join(workdir, os.path.basename(model)))
        audio_cwd = workdir
    else:
        print("    未启用（spec.audio.enabled = false）")

    print("\n⑤ 烧字幕并合成")
    compose(stage1, ass_path, spec["out"], audio_chain, audio_cwd,
            spec.get("crf", 18), spec.get("preset", "medium"))

    # ⑥ 封面
    print("\n⑥ 封面")
    cover = make_cover({**spec, "video": stage1}, workdir,
                       os.path.join(workdir, "cover.png"),
                       at=spec.get("cover", {}).get("at", 0.0))

    print("\n" + "=" * 70)
    print("完成")
    print("=" * 70)
    print(f"  成片：{spec['out']}  ({os.path.getsize(spec['out'])/1024/1024:.1f} MB)")
    if cover:
        print(f"  封面：{cover}")
    print(f"  时长：{probe_duration(spec['out']):.2f}s")
    return spec["out"]


def build_spec_example():
    return {
        "video": r"D:\个人资料\家庭教育\测试\test.mp4",
        "script": r"D:\个人资料\家庭教育\测试\_脚本.txt",
        "out": r"D:\个人资料\家庭教育\测试\_成片.mp4",
        "cut_silence": True,
        "marks": [{"word": "装的", "color": WARM, "bold": True, "scale": 1.12}],
        "punch": {"text": "检查没查出来，不等于孩子在装",
                  "marks": [{"word": "不等于孩子在装", "color": WARM_DEEP, "bold": True}],
                  "at": "end"},
        "cover": {"text": "不等于孩子在装", "at": 1.0},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec")
    ap.add_argument("--workdir")
    ap.add_argument("--example", action="store_true", help="打印剪辑单样例")
    args = ap.parse_args()
    if args.example:
        print(json.dumps(build_spec_example(), ensure_ascii=False, indent=1))
        return
    if not args.spec:
        ap.error("需要 --spec <剪辑单.json>（或用 --example 看样例）")
    spec = json.loads(open(args.spec, encoding="utf-8-sig").read())
    workdir = args.workdir or os.path.join(os.path.dirname(os.path.abspath(spec["out"])), "_过程文件")
    make(spec, workdir)


if __name__ == "__main__":
    main()
