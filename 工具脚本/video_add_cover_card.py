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
    "$PY" 工具脚本/video_add_cover_card.py "成片_01.mp4" --at 1.2         # ⭐ 取"正片第 1.2 秒"那一帧当封面卡
    "$PY" 工具脚本/video_add_cover_card.py "成片_01.mp4" --inplace        # 跑完自动改名覆盖
    "$PY" 工具脚本/video_add_cover_card.py "成片_01.mp4" --dry-run        # 只看命令

⭐⭐ 2026-10-02 加的 `--at`（封面卡取哪一帧）：
    原来写死"克隆第 1 帧"，而**第 1 帧常常正好是闭眼／表情没到位的那一瞬**
    （05 实测：前置的 2 秒静止画面里人闭着眼，很扎眼）。
    `--at T` 改成「抽第 T 秒那一帧 → 循环 N 秒 → 与正片 concat」（画面/时长与老做法等价）。
    ⭐ **T 的选法**：要保持"封面卡上有开头钩子大字"，就取 **0 ~ 钩子时长（本系列 2s）之间**的一帧（如 1.2s）；
    想封面卡干净无字，则取钩子结束之后（如 2.4s）。`--at 0`（默认）＝ 老行为。

⭐⭐ 2026-09-28 加的两件事：
  ① **防重入**：`tpad` **不是幂等的** —— 对已加过封面卡的成片再跑一次，会在前面**再叠 2 秒**（变 4 秒）。
     所以本脚本跑之前会检查「标记文件」与「`_旧版本/` 里的无封面卡备份」；
     命中就**停下报错**，真要重加得加 `--force`（或者更稳：从 `_旧版本/…_无封面卡.mp4` 重做）。
  ② **抽帧标记**：跑完会在成片旁写 `<成片>.cover.json`。
     因为封面卡让**正片整体后移了 N 秒**，而 `subs.ass` 的时间码是相对正片的 ——
     `video_check_frames.py` 靠这个标记**自动把抽帧点后移**（否则看到的画面会早 N 秒，
     于是"字幕有没有遮嘴"根本查不出来，2026-09-28 实测踩过）。
"""
import argparse
import datetime
import json
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


def _probe_path(ffmpeg: str) -> str:
    ffprobe = os.path.join(os.path.dirname(ffmpeg), "ffprobe")
    if os.name == "nt":
        ffprobe += ".exe"
    if not os.path.isfile(ffprobe):
        ffprobe = shutil.which("ffprobe") or ""
    return ffprobe


def _duration(ffmpeg: str, path: str) -> float:
    """成片时长（秒）；探测失败返回 0。用于判断"当前成片到底加没加封面卡"。"""
    ffprobe = _probe_path(ffmpeg)
    if not ffprobe:
        return 0.0
    try:
        p = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", path],
            capture_output=True, text=True, timeout=120)
        return float((p.stdout or "").strip().splitlines()[0])
    except Exception:
        return 0.0


def _cover_mark_path(video: str) -> str:
    return video + ".cover.json"


def _video_fps(ffmpeg: str, src: str) -> str:
    """探测输入帧率 —— 「抽某一帧当封面卡」那条路径要用它（抽帧图与正片同帧率才能 concat）。"""
    ffprobe = os.path.join(os.path.dirname(ffmpeg), "ffprobe")
    if os.name == "nt":
        ffprobe += ".exe"
    if not os.path.isfile(ffprobe):
        ffprobe = shutil.which("ffprobe") or ""
    if not ffprobe:
        return "30"
    try:
        p = subprocess.run(
            [ffprobe, "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=r_frame_rate",
             "-of", "default=nw=1:nk=1", src],
            capture_output=True, text=True, timeout=120)
        s = (p.stdout or "").strip().splitlines()
        s = s[0].strip() if s else ""
        if "/" in s:
            num, den = s.split("/")[:2]
            if den.strip() not in ("", "0"):
                return "%.6g" % (float(num) / float(den))
        if s:
            return s
    except Exception:
        pass
    return "30"


def _build_args_pick_frame(ffmpeg: str, src: str, at: float, seconds: float,
                           bitrate: str, dst: str):
    """`--at T`（T > 0）走这条：**从成片第 T 秒抽一帧**当静止封面卡。

    为什么不用 `tpad`：`tpad=start_mode=clone` 只会克隆**第 1 帧**，
    而第 1 帧常常正好是"闭眼／表情没到位"的那一瞬（2026-10-02，05 实测踩到）。
    → 改为「抽出第 T 秒那一帧 → 循环 N 秒 → 与正片 concat」，音轨用 `adelay` 后移 N 秒。
    ✅ 与 `tpad` 路径**画面/时长等价**，只是把"克隆第 1 帧"换成"克隆第 T 秒那一帧"。

    ⚠️ 返回 `(args, tmpdir)` —— **抽出的那帧要等 ffmpeg 跑完才能删**（调用方负责）。
    """
    import tempfile
    fps = _video_fps(ffmpeg, src)
    tmp = tempfile.mkdtemp(prefix="wb_coverframe_")
    png = os.path.join(tmp, "_cover_frame.png")
    p = subprocess.run(
        [ffmpeg, "-hide_banner", "-y", "-ss", "%.6g" % at, "-i", src,
         "-frames:v", "1", png],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0 or not os.path.isfile(png):
        shutil.rmtree(tmp, ignore_errors=True)
        raise SystemExit("⛔ 抽帧失败（--at %.3gs）：\n%s" % (at, (p.stderr or "")[-800:]))
    ms = int(round(seconds * 1000))
    fc = (
        "[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,"
        "pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p[h];"
        "[1:v]setsar=1,format=yuv420p[m];"
        "[h][m]concat=n=2:v=1:a=0[v];"
        "[1:a]adelay=%d|%d[a]" % (ms, ms)
    )
    args = [ffmpeg, "-hide_banner", "-y",
            "-loop", "1", "-framerate", fps, "-t", "%.6g" % seconds, "-i", png,
            "-i", src,
            "-filter_complex", fc,
            "-map", "[v]", "-map", "[a]",
            "-r", fps,
            "-c:v", "libx264", "-preset", "veryfast", "-b:v", bitrate,
            "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", dst]
    return args, tmp


def _existing_cover_seconds(src: str, ffmpeg: str = ""):
    """探测"这个成片是不是已经加过封面卡"→ (秒数 or None, 依据说明)。

    两条证据（任一命中即判定"已加过"）：
      ① 成片旁的标记文件 `<成片>.cover.json`（本脚本自己写的，最可信）；
      ② `_旧版本/<名>_无封面卡.mp4` 存在 **且当前成片比它长**（`--inplace` 的备份；
         ⚠️ 该目录有 3 天自动清理，可能已不在）。

    ⭐ **2026-10-02 修**：证据 ② 原来**只看"备份存在"**就判定已加过 ——
    可"**从备份重做**"（正是本脚本自己推荐的做法）时备份一定在，于是**必然误拦自己**。
    现在改成**比时长**：当前成片比备份长 ≈ N 秒才算"已加过"；**与备份一样长 → 未加过，放行**。
    """
    mk = _cover_mark_path(src)
    if os.path.exists(mk):
        try:
            return json.load(f).get("seconds"), f"标记文件 {os.path.basename(mk)}"
        except Exception:
            return None, "标记文件解析失败"
    bak = os.path.join(os.path.dirname(src), "_旧版本",
                       os.path.splitext(os.path.basename(src))[0] + "_无封面卡.mp4")
    if os.path.exists(bak):
        rel = os.path.relpath(bak, os.path.dirname(src))
        if not ffmpeg:
            return None, f"备份存在（{rel}）"
        d_cur, d_bak = _duration(ffmpeg, src), _duration(ffmpeg, bak)
        diff = d_cur - d_bak
        if d_cur and d_bak and diff > 0.5:
            return diff, f"比备份长 {diff:.2f}s（备份：{rel}）"
        return None, ""          # 与备份同长 → 当前就是"未加封面卡"状态
    return None, ""


def _write_cover_mark(video: str, seconds: float):
    """在成片旁写抽帧标记，供 `video_check_frames.py` 自动后移时间码。"""
    with open(_cover_mark_path(video), "w", encoding="utf-8") as f:
        json.dump({
            "seconds": round(float(seconds), 3),
            "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "note": "正片前的静止封面卡时长；抽帧自查要按它把时间码后移",
        }, f, ensure_ascii=False, indent=1)
    print(f"   ℹ️ 已写抽帧标记：{os.path.basename(_cover_mark_path(video))}"
          f"（抽帧自查会自动 +{seconds:g}s）")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video", help="成片路径")
    ap.add_argument("--seconds", type=float, default=2.0, help="前置秒数（默认 2）")
    ap.add_argument("--bitrate", default=None,
                    help="视频码率；不指定则**沿用输入成片的码率**（避免重编码降码）")
    ap.add_argument("--inplace", action="store_true", help="跑完自动改名覆盖原文件")
    ap.add_argument("--at", type=float, default=0.0,
                    help="封面卡取**成片第几秒那一帧**（默认 0 ＝ 第 1 帧）。"
                         "第 1 帧闭眼/表情没到位时用它，如 --at 1.2"
                         "（想在封面卡上保留开头钩子大字，就取 0~钩子时长之间的一帧）")
    ap.add_argument("--force", action="store_true",
                    help="已知加过封面卡仍要强行再叠（⛔ 会把 2 秒变 4 秒）")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    src = os.path.abspath(a.video)
    if not os.path.isfile(src):
        raise SystemExit(f"❌ 找不到文件：{src}")

    # ⭐ 防重入（2026-09-28 加）：tpad 不幂等，重复跑会把封面卡叠成 4 秒
    ffmpeg = _ffmpeg()
    if not a.force:
        sec, why = _existing_cover_seconds(src, ffmpeg)
        if why:
            shown = f"{sec:g} 秒" if isinstance(sec, (int, float)) else "若干秒"
            raise SystemExit(
                f"⛔ 这个成片**看起来已经加过封面卡**了（{shown}；依据：{why}）。\n"
                f"   再跑一次会在前面**再叠 {a.seconds:g} 秒**（`tpad` 不是幂等的）。\n"
                f"   ✅ 要重加：从 `_旧版本/<名>_无封面卡.mp4` 出发重做（最稳）；\n"
                f"   ⚠️ 确实要叠加：加 --force（一般不该这么做）。")
    ms = int(round(a.seconds * 1000))
    dst = os.path.splitext(src)[0] + "_封面卡.mp4"

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
    tmpdir = None
    if a.at and a.at > 0.0001:
        # ⭐ 2026-10-02 加：第 1 帧闭眼时，改成"抽第 T 秒那一帧"当封面卡
        args, tmpdir = _build_args_pick_frame(ffmpeg, src, a.at, a.seconds,
                                              bitrate, dst)
        print("封面卡取帧：成片第 %.3g 秒那一帧（不是第 1 帧）" % a.at)
    print("前置封面卡：%.2fs" % a.seconds)
    print("视频码率：%s%s" % (bitrate, "" if a.bitrate else "（沿用输入）"))
    print("输出：", dst)
    if a.dry_run:
        print("命令：", " ".join(args))
        return

    p = subprocess.run(args, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if tmpdir:
        shutil.rmtree(tmpdir, ignore_errors=True)
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
        _write_cover_mark(src, a.seconds)
    else:
        print(f"✅ 完成：{dst}")
        print("   （要让原文件名生效，加 --inplace，或自己改名覆盖）")
        _write_cover_mark(dst, a.seconds)


if __name__ == "__main__":
    main()
