# -*- coding: utf-8 -*-
"""临时：测出该机位下人脸的"眼睛行"在画面中的 y 坐标（按暗像素分布）。

做法：把脸部横向范围裁成一条竖带（默认 x 450~810），转灰度原始数据，
      按行统计「暗像素占比」，打印分布——眼睛所在的那一带有明显峰值。
"""
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")
FFMPEG = r"C:/Users/ZhuanZ/.workbuddy/binaries/ffmpeg/bin/ffmpeg.exe"
V = sys.argv[1]
T = float(sys.argv[2]) if len(sys.argv) > 2 else 1.2
X, W = 450, 360
H = 1920

p = subprocess.run([FFMPEG, "-v", "error", "-ss", "%.3f" % T, "-i", V,
                    "-vf", "crop=%d:%d:%d:0,format=gray" % (W, H, X),
                    "-f", "rawvideo", "-"], capture_output=True)
raw = p.stdout
assert len(raw) >= W * H, "取帧失败：%d bytes" % len(raw)

rows = []
for y in range(H):
    line = raw[y * W:(y + 1) * W]
    dark = sum(1 for v in line if v < 70)
    rows.append(dark / W)

print("每 40 行的暗像素占比（0~1）：")
for y0 in range(400, 1200, 40):
    seg = rows[y0:y0 + 40]
    avg = sum(seg) / 40
    bar = "#" * int(avg * 120)
    print("  y %4d~%-4d  %.3f  %s" % (y0, y0 + 40, avg, bar))
best = max(range(400, 1200), key=lambda y: rows[y])
print()
print("暗部峰值行：y = %d（占比 %.3f）" % (best, rows[best]))
