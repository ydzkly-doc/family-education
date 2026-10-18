# -*- coding: utf-8 -*-
"""单段实拍偏暗修复（多段口播条某一段整体欠曝时用）。

场景：同机位连拍多段，其中一段拍摄时补光不足 → 该段整段偏暗（实测脸 Y 比
其余段低约 20），且这种暗是【整段曝光低】不是局部阴影。后期在【源段】上
提亮，再整条重跑 video_make.py，字幕/金句卡是后烧的不受影响（方案A）。

为什么只在源段修、不直接在成片上套滤镜：
  成片上提亮会把白色字幕/金句卡一起拉亮、高光发虚；从源段修最干净。
为什么提亮后仍让管道跑 color_match：
  video_visual.compute_gains 以全段平均 RGB 做带上下限裁剪的每通道增益；
  源段手动补齐后它只做轻微收敛（实测该段增益≈0.888，把稍过的一档压回），
  最终四段亮度齐平、无色差跳变，且不抵消手动提亮。

推荐三档（eq；提中暗部为主、微抬对比饱和，避免白衫/白墙过曝）：
  light  gamma=1.12 brightness=0.015 contrast=1.02 saturation=1.06
  mid    gamma=1.22 brightness=0.025 contrast=1.04 saturation=1.10   ← 默认常用
  strong gamma=1.32 brightness=0.035 contrast=1.06 saturation=1.12
判据：提完最暗帧的脸部 Y≈120（与其余段齐平），且原本最亮帧过曝像素(Y>=248)
占比仍 < ~0.5%、白衫保留纹理。段内不同时刻亮度本身不均时，宁选 light/mid，
让最亮帧不过冲，靠管道 color_match 再收敛。

用法：
  # 出某源文件在 t 秒的三档对比帧 + 亮度测量（先选档，不动视频）
  python grade_dark_segment.py compare 源.MOV --times 12 40 75
  # 按选中档生成调色段（视频重编码 crf16、音频流复制，几何/帧率/时长不变）
  python grade_dark_segment.py apply 源.MOV 输出.MOV --preset mid
"""
import argparse
import os
import subprocess
import sys

import numpy as np
from PIL import Image

FFMPEG = r"C:\Users\ZhuanZ\.workbuddy\binaries\ffmpeg\bin\ffmpeg.exe"
FFPROBE = r"C:\Users\ZhuanZ\.workbuddy\binaries\ffmpeg\bin\ffprobe.exe"

PRESETS = {
    "light":  "eq=brightness=0.015:gamma=1.12:contrast=1.02:saturation=1.06",
    "mid":    "eq=brightness=0.025:gamma=1.22:contrast=1.04:saturation=1.10",
    "strong": "eq=brightness=0.035:gamma=1.32:contrast=1.06:saturation=1.12",
}


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def duration(p):
    r = run([FFPROBE, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", p])
    return float(r.stdout.strip())


def grab(src, t, out):
    run([FFMPEG, "-y", "-ss", str(t), "-i", src, "-frames:v", "1",
         "-q:v", "3", out, "-loglevel", "error"])


def measure(p):
    a = np.asarray(Image.open(p).convert("L"))
    h, w = a.shape
    face = a[int(h * 0.40):int(h * 0.66), int(w * 0.28):int(w * 0.74)].mean()
    shirt = a[int(h * 0.70):int(h * 0.95), :].mean()
    over = (a >= 248).mean() * 100
    return face, shirt, over


def cmd_compare(src, times, workdir):
    os.makedirs(workdir, exist_ok=True)
    for t in times:
        s = os.path.join(workdir, f"src_{t}.jpg")
        grab(src, t, s)
        fa, sh, ov = measure(s)
        print(f"t={t:>3} 原片  脸Y={fa:6.1f} 衫Y={sh:6.1f} 过曝{ov:4.2f}%")
        for name, vf in PRESETS.items():
            o = os.path.join(workdir, f"{name}_{t}.jpg")
            run([FFMPEG, "-y", "-i", s, "-vf", vf, "-frames:v", "1",
                 "-q:v", "3", o, "-loglevel", "error"])
            fa, sh, ov = measure(o)
            print(f"       {name:<6} 脸Y={fa:6.1f} 衫Y={sh:6.1f} 过曝{ov:4.2f}%")
    print("对比帧目录：", workdir)


def cmd_apply(src, dst, preset):
    vf = PRESETS[preset]
    d0 = duration(src)
    r = run([FFMPEG, "-y", "-i", src,
             "-map", "0:v:0", "-map", "0:a:0",
             "-vf", vf,
             "-c:v", "libx264", "-preset", "medium", "-crf", "16",
             "-pix_fmt", "yuv420p", "-c:a", "copy",
             "-movflags", "+faststart", dst])
    if not os.path.exists(dst):
        print(r.stderr[-2000:]); sys.exit(1)
    d1 = duration(dst)
    assert abs(d0 - d1) < 0.02, f"时长变了 {d0} -> {d1}"
    print(f"OK {preset}：{d0:.3f}s -> {d1:.3f}s（一致）  "
          f"{os.path.getsize(dst)/1048576:.1f} MB  -> {dst}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c1 = sub.add_parser("compare")
    c1.add_argument("src"); c1.add_argument("--times", type=float, nargs="+",
                                            default=[10, 40, 70])
    c1.add_argument("--workdir", default="_grade_compare")
    c2 = sub.add_parser("apply")
    c2.add_argument("src"); c2.add_argument("dst")
    c2.add_argument("--preset", choices=list(PRESETS), default="mid")
    a = ap.parse_args()
    if a.cmd == "compare":
        cmd_compare(a.src, a.times, a.workdir)
    else:
        cmd_apply(a.src, a.dst, a.preset)


if __name__ == "__main__":
    main()
