# -*- coding: utf-8 -*-
"""
title_mock.py —— 常驻标题「秒级样式预演」（2026-10-13 立）

为什么有这个脚本：
  常驻标题全片挂顶、压在实拍背景上，配色/字号**只有叠到真实画面上才看得出合不合适**。
  但烧一整条成片要约 13 分钟（要拼接/剪停顿/ASR/合成），为调字号重烧极不划算。
  → 开工前先用本脚本：自动从素材抽「最亮一帧 + 最暗一帧」当背景，把当前标题样式
    （或几个候选字号）叠上去出图，**几秒**出对比，确认后再烧整片。

不做的事：不剪辑、不 ASR、不合成视频、不改任何成片；只产静态 PNG。

用法：
  python title_mock.py --md 文案.md --videos-dir 素材目录 [--out 预演图.png]
                       [--sizes 68,76,82] [--times 1.0,30,60]
  · --sizes   要对比的字号档（逗号分隔）；缺省给 68（现基准）与 82（底部强调/金句号）
  · --times   手动指定抽帧秒数（逗号分隔），不给则自动在每个素材若干位置抽帧选最亮/最暗
  · --out     输出 PNG（默认写到素材同级 _标题预演/标题预演.png）

判读：挑一个「在亮底和暗底都清楚、且视觉分量不小于底部金句」的字号；系列色若在亮底发飘，
      回到 MD 的「色：#xxxxxx」换更深/更亮的色重跑本脚本，别动主管道。
"""
import argparse
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import md_spec as M
import paths
import video_build_ass as B

FFMPEG = paths.ffmpeg_path()
FFPROBE = os.path.join(os.path.dirname(FFMPEG),
                       "ffprobe.exe" if os.name == "nt" else "ffprobe")
if not os.path.exists(FFPROBE):
    FFPROBE = shutil.which("ffprobe") or FFPROBE

OUT_W, OUT_H = 1080, 1920
VIDEO_EXTS = (".mp4", ".mov", ".m4v", ".mkv", ".avi")


def log(*a):
    print("[预演]", *a, flush=True)


def list_videos(videos_dir):
    files = [os.path.join(videos_dir, f) for f in os.listdir(videos_dir)
             if f.lower().endswith(VIDEO_EXTS) and not f.startswith("_")]
    return sorted(files)


def duration(video):
    p = subprocess.run([FFMPEG, "-hide_banner", "-i", video],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", p.stderr or "")
    if not m:
        return 0.0
    h, mi, s = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(s)


def grab_frame(video, t, out_png):
    """抽单帧并统一到 1080x1920（与成片同裁切口径），返回是否成功。"""
    vf = (f"scale={OUT_W}:{OUT_H}:force_original_aspect_ratio=increase,"
          f"crop={OUT_W}:{OUT_H}")
    r = subprocess.run([FFMPEG, "-hide_banner", "-y", "-ss", f"{t:.2f}",
                        "-i", os.path.abspath(video), "-vf", vf,
                        "-frames:v", "1", os.path.abspath(out_png),
                        "-loglevel", "error"],
                       capture_output=True, text=True)
    return os.path.exists(out_png)


def frame_luma(png):
    """用 Pillow 算平均亮度 0~255（无 Pillow 时退回中性值）。"""
    try:
        from PIL import Image, ImageStat
        im = Image.open(png).convert("L").resize((64, 114))
        return ImageStat.Stat(im).mean[0]
    except Exception:
        return 128.0


def pick_bg_frames(videos, workdir, manual_times=None):
    """返回 (亮底png, 暗底png)。自动在每个素材 15%/50%/85% 处抽帧选最亮/最暗。"""
    cands = []
    if manual_times:
        # 手动：在第一个（或轮流）素材指定秒点抽
        for i, t in enumerate(manual_times):
            v = videos[min(i, len(videos) - 1)]
            p = os.path.join(workdir, f"cand_m{i}.png")
            if grab_frame(v, float(t), p):
                cands.append(p)
    else:
        for vi, v in enumerate(videos):
            d = duration(v)
            if d <= 0:
                continue
            for k, frac in enumerate((0.15, 0.5, 0.85)):
                p = os.path.join(workdir, f"cand_{vi}_{k}.png")
                if grab_frame(v, d * frac, p):
                    cands.append(p)
    if not cands:
        raise RuntimeError("没能从素材抽到任何帧，请检查 --videos-dir / ffmpeg")
    scored = [(frame_luma(p), p) for p in cands]
    scored.sort(key=lambda x: x[0])
    dark = scored[0][1]
    bright = scored[-1][1]
    log(f"抽帧 {len(cands)} 张：最亮 {scored[-1][0]:.0f} / 最暗 {scored[0][0]:.0f}")
    return bright, dark


def render_title_png(bg_png, item, size, ass_dir, tag, ruler=None):
    """用 build_ass 生成常驻标题 ASS，叠到背景帧上出单张 1080x1920 PNG。

    ruler：可选 dict(text, marks)——在底部叠一条固定 82 号【强调】金句当标尺，
           用来直接判断"顶部标题 vs 底部金句"的字号协调关系。
    """
    ass_path = os.path.join(ass_dir, f"mock_{tag}.ass")
    ev = dict(item)
    ev["start"], ev["end"], ev["style"] = 0.0, 2.0, "常驻标题"
    ev["size"] = size                       # item 级字号覆盖（build_ass 会在 title_persist 分支采用）
    ev["anim"] = ""                         # ⭐ 静帧抓 t=0：必须关 300ms 淡入，否则首帧全透明（同封面原理）
    ospec = {"title_persist": [ev]}
    if ruler:
        ospec["punch"] = [{
            "start": 0.0, "end": 2.0, "text": ruler["text"],
            "marks": ruler.get("marks"), "style": "强调",   # 【强调】样式本身即 82 号
            "anim": "",
        }]
    B.build_ass(ospec, ass_path, wrap=True)
    out_png = os.path.join(ass_dir, f"mock_{tag}.png")
    # ass 只传文件名 + cwd=ass_dir，规避中文绝对路径解析问题
    subprocess.run([FFMPEG, "-hide_banner", "-y", "-i", os.path.abspath(bg_png),
                    "-vf", f"ass={os.path.basename(ass_path)}",
                    "-frames:v", "1", os.path.abspath(out_png),
                    "-loglevel", "error"],
                   cwd=ass_dir, check=True)
    return out_png


def label_image(png, text):
    """在图顶部加一行字号标签（Pillow）。"""
    try:
        from PIL import Image, ImageDraw
        im = Image.open(png).convert("RGB")
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, OUT_W, 70], fill=(0, 0, 0))
        d.text((24, 18), text, fill=(255, 255, 0))
        im.save(png)
    except Exception:
        pass


def make_contact(images, cols, out_png):
    """把多张 1080x1920 拼成一张对比图（缩到 1/3，便于一屏看全）。"""
    from PIL import Image
    thumb_w, thumb_h = 360, 640
    rows = (len(images) + cols - 1) // cols
    canvas = Image.new("RGB", (thumb_w * cols, thumb_h * rows), (30, 30, 30))
    for i, p in enumerate(images):
        im = Image.open(p).convert("RGB").resize((thumb_w, thumb_h))
        canvas.paste(im, ((i % cols) * thumb_w, (i // cols) * thumb_h))
    canvas.save(out_png)


def main():
    ap = argparse.ArgumentParser(description="常驻标题秒级样式预演（只出静态图、不烧片）")
    ap.add_argument("--md", required=True)
    ap.add_argument("--videos-dir", required=True)
    ap.add_argument("--out", default="")
    ap.add_argument("--sizes", default="68,76,82")
    ap.add_argument("--times", default="")
    args = ap.parse_args()

    spec = M.parse_md(args.md)
    item = spec.get("title_persist")
    if not item:
        sys.exit("该 MD 不是「常驻标题」版本，或没有可预演的常驻标题（先在「上屏方案」选版本=常驻标题）。")
    log(f"标题＝{item['text']}　重点色＝{item.get('color')}")

    videos = list_videos(args.videos_dir)
    if not videos:
        sys.exit(f"素材目录没有视频：{args.videos_dir}")
    log(f"素材 {len(videos)} 个")

    out_png = args.out or os.path.join(args.videos_dir, "..", "_标题预演", "标题预演.png")
    out_png = os.path.abspath(out_png)
    os.makedirs(os.path.dirname(out_png), exist_ok=True)
    workdir = os.path.join(os.path.dirname(out_png), "_tmp")
    os.makedirs(workdir, exist_ok=True)

    times = [float(x) for x in args.times.split(",") if x.strip()] or None
    bright, dark = pick_bg_frames(videos, workdir, times)

    sizes = [int(x) for x in args.sizes.split(",") if x.strip()]

    # 底部标尺：用本篇结尾金句（V_TITLE 下它走底部【强调】82 号），让标题与之同屏比大小
    ruler = None
    if spec.get("punch"):
        p0 = spec["punch"][0]
        ruler = {"text": p0.get("text", ""), "marks": p0.get("marks")}
        log(f"底部标尺（82 号金句）＝{ruler['text']}")

    # 每档出两张：亮底 / 暗底；底部都带 82 号金句标尺
    shots = []
    for s in sizes:
        for bg_name, bg in (("亮底", bright), ("暗底", dark)):
            tag = f"{s}_{bg_name}"
            png = render_title_png(bg, item, s, workdir, tag, ruler=ruler)
            label_image(png, f"顶部标题 {s} 号 / {bg_name}（底部金句固定 82 号）")
            shots.append(png)
            log(f"出图：标题 {s} 号 × {bg_name}")

    make_contact(shots, cols=2, out_png=out_png)
    log("完成 →", out_png)
    print(out_png)


if __name__ == "__main__":
    main()
