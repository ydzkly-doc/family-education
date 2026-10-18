# -*- coding: utf-8 -*-
"""前置 9:16 封面卡（默认 2 秒）+ 响度归一，输出最终成片。

为什么单独有这个脚本（2026-10-17 三连踩坑后沉淀，勿再手搓命令）：
  1) ffmpeg 必须用受管完整版绝对路径：
       C:\\Users\\<user>\\.workbuddy\\binaries\\ffmpeg\\bin\\ffmpeg.exe
     - shell 里裸写 `ffmpeg`：PATH 里没有（video_make.py 内部自己解析了绝对路径，
       不代表全局可用）。
     - 搜出来的 D:\\Program Files\\JianyingPro\\...\\ffmpeg.exe 是【剪映裁剪版】，
       不认 -crf、编码器被砍（报 Unrecognized option 'crf'），绝不能用。
  2) 封面卡必须用 overlay 盖在正片 tpad 补出来的开头黑场上：
       [1:v]tpad=start_duration=2[base]; [0:v][...]; [base][card]overlay=enable='lt(t,2)'
     ⛔ 只对 [1:v] 做 tpad 而不 overlay 输入 0 的封面图 => 封面图被丢弃，
        片头是 2 秒纯黑（2026-10-17 真实返工一次）。
  3) 用 subprocess【列表参数】调用，中文路径不经 shell/代码页
     （.bat 里中文路径会按 GBK 乱码；别用 .bat 包）。

用法：
  python prepend_cover.py <封面卡9x16.png> <无卡底版.mp4> <输出.mp4> [秒数=2]
响度目标固定 I=-14 / TP=-1.5 / LRA=11（动态单遍，本系列实测可达约 -14.2 LUFS）。
编码 CRF 21（实测约 5 Mbps，体积约为旧 linear 版一半，画质一致）。
"""
import os
import sys
import subprocess

FFMPEG = r"C:\Users\ZhuanZ\.workbuddy\binaries\ffmpeg\bin\ffmpeg.exe"


def build(card: str, base: str, out: str, secs: float = 2.0) -> None:
    for p in (card, base):
        if not os.path.exists(p):
            raise FileNotFoundError(p)
    if not os.path.exists(FFMPEG):
        raise FileNotFoundError("受管 ffmpeg 不存在: " + FFMPEG)
    s = str(secs)
    fc = (
        f"[1:v]tpad=start_duration={s},setpts=PTS-STARTPTS[base];"
        f"[0:v]setpts=PTS-STARTPTS[card];"
        f"[base][card]overlay=0:0:enable='lt(t,{s})'[v];"
        f"[1:a]aresample=48000,adelay={int(secs * 1000)}|{int(secs * 1000)},"
        f"loudnorm=I=-14:TP=-1.5:LRA=11:print_format=summary[a]"
    )
    cmd = [
        FFMPEG, "-y",
        "-loop", "1", "-t", s, "-i", card,
        "-i", base,
        "-filter_complex", fc,
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "21",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-movflags", "+faststart",
        out,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    # loudnorm 小结打印在 stderr
    tail = r.stderr[-1800:]
    if not os.path.exists(out) or os.path.getsize(out) == 0:
        raise RuntimeError("输出失败，ffmpeg 尾部日志:\n" + tail)
    print(tail)
    print("OK ->", out, f"{os.path.getsize(out) / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)
    sec = float(sys.argv[4]) if len(sys.argv) >= 5 else 2.0
    build(sys.argv[1], sys.argv[2], sys.argv[3], sec)
