# -*- coding: utf-8 -*-
"""探测成片尾部静音：报告总时长 / 音轨时长 / 尾部静音起点与长度。

用法：
    python _probe_tail_silence.py <视频1> [<视频2> ...]
"""
import json
import os
import subprocess
import sys

FFPROBE = r"C:/Users/ZhuanZ/.workbuddy/binaries/ffmpeg/bin/ffprobe.exe"
FFMPEG = r"C:/Users/ZhuanZ/.workbuddy/binaries/ffmpeg/bin/ffmpeg.exe"


def probe(f):
    cmd = [FFPROBE, "-v", "error", "-print_format", "json",
           "-show_format", "-show_streams", f]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return json.loads(r.stdout)


def tail_silence(f, noise="-45dB", min_dur=0.25):
    """返回 [(静音起点, 静音终点, 时长), ...]"""
    cmd = [FFMPEG, "-hide_banner", "-nostats", "-i", f,
           "-af", f"silencedetect=noise={noise}:d={min_dur}",
           "-f", "null", "-"]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = []
    start = None
    for line in r.stderr.splitlines():
        if "silence_start:" in line:
            try:
                start = float(line.split("silence_start:")[1].strip().split()[0])
            except ValueError:
                start = None
        elif "silence_end:" in line:
            try:
                seg = line.split("silence_end:")[1].strip()
                end = float(seg.split()[0])
                rest = seg.split("|")
                dur = float(rest[1].split(":")[1]) if len(rest) > 1 else None
                if start is not None:
                    out.append((start, end, dur))
            except (ValueError, IndexError):
                pass
            start = None
    return out


def main():
    for f in sys.argv[1:]:
        if not os.path.exists(f):
            print(f"[跳过] 不存在：{f}")
            continue
        print("=" * 72)
        print(f)
        info = probe(f)
        fmt_dur = float(info["format"]["duration"])
        v = next((s for s in info["streams"] if s["codec_type"] == "video"), {})
        a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
        print(f"  容器总时长     : {fmt_dur:.3f}s")
        print(f"  视频流时长     : {float(v.get('duration', 0)):.3f}s  {v.get('width')}x{v.get('height')}")
        if a:
            print(f"  音频流时长     : {float(a.get('duration', 0)):.3f}s  {a.get('codec_name')}")
            print(f"  视频-音频差    : {fmt_dur - float(a.get('duration', 0)):.3f}s")
        else:
            print("  ⛔ 无音频流")
        segs = tail_silence(f)
        print(f"  静音段（≤-45dB,≥0.25s）：{len(segs)} 段")
        for s, e, d in segs:
            tag = "  ← 尾部" if e >= fmt_dur - 0.12 else ""
            print(f"    {s:8.2f}s → {e:8.2f}s  长 {d if d else (e - s):.2f}s{tag}")
        if segs and segs[-1][1] >= fmt_dur - 0.12:
            s = segs[-1][0]
            print(f"  ⚠️ 尾部静音起点 = {s:.2f}s （正片有效长 {s:.2f}s，静音 {(fmt_dur - s):.2f}s）")


if __name__ == "__main__":
    main()
