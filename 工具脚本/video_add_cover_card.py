#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
给成片前置 N 秒静止「封面卡」—— 克隆第一帧当作停留画面，正片整体后移，音画仍严格对齐。

为什么需要它（2026-09-25 立）：
    管道把「开头钩子」直接叠在**正片第一帧**上。而实拍口播常常**开口很早**
    （本条素材第 0.39 秒就开口）→ 钩子大字必然压住开口画面，观众看到的
    是"人已经在讲，字还挂在脸上"。
    解法：出片后**在开头克隆第一帧并停留 N 秒**（这段静止画面里已经有钩子大字，
    因为它是烧在画面里的），正片整体后移 N 秒。
    → 钩子时长设成 N 秒，正好落在静止画面上，**正片一开口就没有字遮挡**。
    → 前置的这段静止画面**本身就是第一帧**，所以"平台拿第一帧当封面"照样满足。

⚠️ 必须重编码（`-c copy` 做不了 tpad）→ ⭐ **码率默认「沿用输入成片的码率」**（2026-09-26 改）：
   原来写死 `-b:v 6M -crf 20`，会把 **10 Mbps 的成片重压成 5.2 Mbps**
   （实测：328 MB → 185 MB）——**等于白降一次画质**（用户要求的是 8~10M）。
   现在先探测输入码率再沿用，这一步不会再意外降码。
   > ℹ️ 口径：本系列成片默认 `bitrate=10M`（官方"建议 ≥10Mbps"）；
   > ⛔ **别再写"视频号上限 6000 kbps"**——那是第三方说法，已被推翻。
⚠️ ffmpeg 不能读写同一个文件 → 默认输出 `<原名>_封面卡.mp4`，跑完请自行改名覆盖。
ℹ️ `--inplace` 时会把**加封面卡前的成片**备份到 `<成片目录>/_旧版本/<名>_无封面卡.mp4` ——
   它不是"另一个产物"，只是"想改封面卡秒数时不必重跑整条管道"的回头路。

用法：
    PY="C:/Users/ZhuanZ/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
    "$PY" 工具脚本/video_add_cover_card.py "成片_01.mp4"                  # 默认前置 2 秒
    "$PY" 工具脚本/video_add_cover_card.py "成片_01.mp4" --seconds 2.5
    "$PY" 工具脚本/video_add_cover_card.py "成片_01.mp4" --inplace        # 跑完自动改名覆盖
    "$PY" 工具脚本/video_add_cover_card.py "成片_01.mp4" --dry-run        # 只看命令
"""
import argparse
import os
import shutil
import subprocess
import sys


def _ffmpeg() -> str:
    """优先用技能里解析出的 ffmpeg，找不到就退回 PATH。"""
    skill_scripts = os.path.expanduser(
        r"~/.workbuddy/skills/ffmpeg-vertical-video-pipeline/scripts")
    if os.path.isdir(skill_scripts):
        sys.path.insert(0, skill_scripts)
        try:
            import paths  # type: ignore
            return paths.ffmpeg_path()
        except Exception:
            pass
    return shutil.which("ffmpeg") or "ffmpeg"


def _video_bitrate(ffmpeg: str, src: str) -> str:
    """探测输入成片的视频码率（沿用它，避免这一步重编码把码率压低）。"""
    ffprobe = os.path.join(os.path.dirname(ffmpeg), "ffprobe")
    if os.name == "nt":
        ffprobe += ".exe"
    if not os.path.isfile(ffprobe):
        ffprobe = shutil.which("ffprobe") or ""
    if not ffprobe:
        return ""
    try:
        p = subprocess.run(
            [ffprobe, "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=bit_rate",
             "-of", "default=nw=1:nk=1", src],
            capture_output=True, text=True, timeout=120)
        val = [x for x in (p.stdout or "").strip().splitlines() if x.strip()]
        if val and val[0].strip().isdigit() and int(val[0]) > 0:
            return "%dk" % (int(val[0]) // 1000)
    except Exception:
        pass
    return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video", help="成片路径")
    ap.add_argument("--seconds", type=float, default=2.0, help="前置秒数（默认 2）")
    ap.add_argument("--bitrate", default=None,
                    help="视频码率；不指定则**沿用输入成片的码率**（避免重编码降码）")
    ap.add_argument("--inplace", action="store_true", help="跑完自动改名覆盖原文件")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    src = os.path.abspath(a.video)
    if not os.path.isfile(src):
        raise SystemExit(f"❌ 找不到文件：{src}")
    ms = int(round(a.seconds * 1000))
    dst = os.path.splitext(src)[0] + "_封面卡.mp4"

    ffmpeg = _ffmpeg()
    bitrate = a.bitrate or _video_bitrate(ffmpeg, src) or "10M"

    args = [
        ffmpeg, "-hide_banner", "-y",
        "-i", src,
        "-vf", f"tpad=start_duration={a.seconds:g}:start_mode=clone",
        "-af", f"adelay={ms}|{ms}",
        "-c:v", "libx264", "-preset", "veryfast", "-b:v", bitrate,
        "-c:a", "aac", "-b:a", "192k",
        dst,
    ]
    print("前置封面卡：%.2fs" % a.seconds)
    print("视频码率：%s%s" % (bitrate, "" if a.bitrate else "（沿用输入）"))
    print("输出：", dst)
    if a.dry_run:
        print("命令：", " ".join(args))
        return

    p = subprocess.run(args, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if p.returncode != 0:
        print("!! 失败，最后 15 行：")
        for line in (p.stderr or "").splitlines()[-15:]:
            print("   ", line)
        raise SystemExit(1)

    if a.inplace:
        # ⚠️ 备份放进 `_旧版本/`（2026-09-26 改）：原来直接放在成片目录里，
        #    会和真正的成片混在一起被误认（用户实测就问过"成片_01_无封面卡.mp4 是做什么用的"）。
        #    它只有一个用途：**想换封面卡秒数时不必重跑整条管道**。
        old_dir = os.path.join(os.path.dirname(src), "_旧版本")
        os.makedirs(old_dir, exist_ok=True)
        bak = os.path.join(old_dir,
                           os.path.splitext(os.path.basename(src))[0] + "_无封面卡.mp4")
        if os.path.exists(bak):
            os.remove(bak)
        os.rename(src, bak)
        os.rename(dst, src)
        print(f"✅ 已覆盖：{src}")
        print(f"   （加封面卡前的版本已备份到 {os.path.relpath(bak, os.path.dirname(src))}）")
    else:
        print(f"✅ 完成：{dst}")
        print("   （要让原文件名生效，加 --inplace，或自己改名覆盖）")


if __name__ == "__main__":
    main()
