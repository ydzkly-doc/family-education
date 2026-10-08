# -*- coding: utf-8 -*-
"""取帧候选：把同一视频的若干时间点抽帧 → 裁同一区域 → 放大 → 横排成一张对比图。

⭐ 为什么需要它（hk53 的配套）：
   出片后要核对「封面那一帧，眼睛有没有闭」。
   ⚠️ **看缩略图/整图判断不可靠**（2026-10-05 在 03、06 上各踩一次：
      整图看着"还行"，放大后发现是半闭眼）。必须
      **裁头部区域 + 放大 + 并排**，才能一眼分出哪一帧睁得最开。

用法：
   video_cover_frame_check.py <视频> --times 0.6,1.2,1.6,2.0
   video_cover_frame_check.py <视频> --times 0.6,1.2 --head     # 用本系列默认头部区域
   可选：--crop W:H:X:Y（默认 520:560:390:620）｜--scale 500｜--out 图.png

输出：横排对比图（默认 <视频同目录>/_过程文件/取帧候选.png），
      并在 stdout 打印"第几格 = 第几秒"（从左到右），便于对着图挑帧。
"""
import argparse
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

FFMPEG = r"C:/Users/ZhuanZ/.workbuddy/binaries/ffmpeg/bin/ffmpeg.exe"

# 本系列（《改善你的亲子关系》，1080x1920 竖屏、人像居中）的**眼部**默认区域
# ⚠️ 判据：眼睛要落在裁切区的**中部**——若眼睛贴顶/贴底，说明机位变了，用 --crop 调整
#    2026-10-05 像素级实测该系列：**眼位 ≈ y 950**（脸 x 450~810）；眉毛 ≈ y 860（浅色、不显眼）
#    ⛔ **别把"暗像素峰值"直接当眼睛**：该机位下**寸头发是黑色、横跨整个宽度**，
#       顶部 y 680~740 的暗峰其实是**头顶**（整条暗带）——眼睛是**左右成对的小暗块**，这才可靠。
HEAD_CROP = "400:320:430:790"


def grab(ffmpeg, src, t, crop, scale, out):
    vf = f"crop={crop},scale={scale}:-1"
    p = subprocess.run([ffmpeg, "-v", "error", "-ss", "%.3f" % t, "-i", src,
                        "-frames:v", "1", "-vf", vf, "-y", out],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode == 0 and os.path.exists(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--times", required=True, help="逗号分隔的秒数，如 0.6,1.2,1.6,2.0")
    ap.add_argument("--crop", default=HEAD_CROP)
    ap.add_argument("--head", action="store_true", help="用本系列默认头部区域（等同默认）")
    ap.add_argument("--scale", type=int, default=560)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    times = [float(x) for x in a.times.replace("，", ",").split(",") if x.strip()]
    if not times:
        print("给我至少一个时间点")
        return 2
    out_png = a.out or os.path.join(os.path.dirname(os.path.abspath(a.video)),
                                    "_过程文件", "取帧候选.png")
    os.makedirs(os.path.dirname(out_png), exist_ok=True)
    tmpdir = os.path.join(os.path.dirname(out_png), "_cand")
    os.makedirs(tmpdir, exist_ok=True)

    parts, ok_times = [], []
    for i, t in enumerate(times, 1):
        f = os.path.join(tmpdir, "c%02d.png" % i)
        if grab(FFMPEG, a.video, t, a.crop, a.scale, f):
            parts.append(f)
            ok_times.append(t)
        else:
            print("  ⚠️ %.3fs 抽帧失败，跳过" % t)
    if not parts:
        print("一帧都没抽到")
        return 1

    args = [FFMPEG, "-v", "error"]
    for p in parts:
        args += ["-i", p]
    if len(parts) == 1:
        # ⚠️ 只有 1 帧时不能用 hstack（ffmpeg 不支持单输入），直接另存
        fc = "[0]null"
    else:
        fc = "".join("[%d]" % i for i in range(len(parts))) + \
             "hstack=inputs=%d" % len(parts)
    args += ["-filter_complex", fc, "-frames:v", "1", "-y", out_png]
    p = subprocess.run(args, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if p.returncode != 0:
        print("拼图失败：", (p.stderr or "")[-300:])
        return 1

    print("对比图：%s" % out_png)
    print("从左到右 ↓（裁切区 %s，宽 %dpx）" % (a.crop, a.scale))
    print("   " + " ｜ ".join("第%d格=%.2fs" % (i, t) for i, t in enumerate(ok_times, 1)))
    print("📌 判据：挑**眼睛睁开、眼白露出最多**的那一帧；闭眼/半闭一律不选。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
