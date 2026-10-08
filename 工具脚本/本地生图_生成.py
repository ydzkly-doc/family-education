#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地文生图 · 生成封装（local-imagegen）
================================================
把 D:\\local-imagegen 的 stable-diffusion.cpp 包成一条命令，供公众号/视频号内容生产直接调用。
不联网、不要账号、不耗积分、不加 AI 水印。

用法：
    python 工具脚本/本地生图_生成.py --prompt "温暖的门缝透光" --preset cover --out "封面.jpg"
    python 工具脚本/本地生图_生成.py --prompt "窗边静物" --preset card --out "底图.jpg"
    python 工具脚本/本地生图_生成.py --prompt "..." --preset raw --out "原图.png" --batch 3

为什么要有这层封装（三个坑，见 工具脚本/本地生图_说明.md）：
  ① sd-cli.exe 收到中文路径参数会被 GBK 双重编码搞坏 -> 一律先写到纯 ASCII 的临时目录
  ② sd-cli.exe 写不进仓库外目录，也写不进带中文的工作区路径 -> 用 TEMP（沙箱允许）做中转
  ③ 出图是 512x512 正方形 -> 按用途裁切/合成/压缩成目标规格
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

try:
    from PIL import Image, ImageEnhance, ImageFilter
except ImportError:  # pragma: no cover
    sys.exit("需要 Pillow：请用带 Pillow 的 Python 运行（DSH 自带 python 已含）")

# ---------------------------------------------------------------- 默认配置
ROOT = Path(os.environ.get("LOCAL_IMAGEGEN_ROOT", r"D:\local-imagegen"))
EXE = ROOT / "bin-vulkan" / "sd-cli.exe"          # 核显版；CPU 版慢约 3.7 倍
MODEL = ROOT / "models" / "DreamShaper8_LCM.safetensors"

# 预设：比例 / 成品尺寸 / 体积上限 / 后处理方式
PRESETS = {
    # 公众号长文封面：SOP 封面规范 —— 2.35:1、核心意象居中方形安全区、≤200KB
    "cover": dict(ratio=(1200, 511), limit_kb=200, mode="cover_safe", quality=94),
    # 卡片文章底图：SOP —— 3:4、单张 <100KB、底图一律柔化
    "card":  dict(ratio=(900, 1200), limit_kb=100, mode="soft",      quality=88, blur=6, brightness=0.85),
    # 原样输出
    "raw":   dict(ratio=None,        limit_kb=None, mode="raw",      quality=95),
}


def log(msg: str) -> None:
    print(msg, flush=True)


def cover_resize(im: Image.Image, w: int, h: int) -> Image.Image:
    """按 cover 方式缩放后居中裁切，保证不出现黑边"""
    s = max(w / im.width, h / im.height)
    nw, nh = max(w, int(im.width * s + 0.5)), max(h, int(im.height * s + 0.5))
    im = im.resize((nw, nh), Image.LANCZOS)
    return im.crop(((nw - w) // 2, (nh - h) // 2, (nw - w) // 2 + w, (nh - h) // 2 + h))


def save_under(img: Image.Image, path: Path, limit_kb: int | None, start_q: int) -> tuple[int, int]:
    """按体积上限逐档降质量；limit_kb 为 None 时只存一次"""
    q = start_q
    if limit_kb is None:
        img.save(path, optimize=True)
        return q, path.stat().st_size // 1024
    while q >= 40:
        img.save(path, "JPEG", quality=q, optimize=True)
        if path.stat().st_size <= limit_kb * 1024:
            break
        q -= 4
    return q, path.stat().st_size // 1024


def generate_one(prompt: str, seed: int | None, steps: int, size: int,
                 cfg: float, out: Path) -> Path | None:
    """调 sd-cli.exe 出一张原图。

    out 必须是纯 ASCII 路径：sd-cli 收到中文路径参数会被 GBK 双重编码搞坏。
    而且不要放在 TEMP 的子目录里 —— 沙箱只授权 TEMP 根目录本身。
    """
    if out.exists():
        out.unlink()
    if not EXE.exists():
        sys.exit(f"找不到程序：{EXE}")
    if not MODEL.exists():
        sys.exit(f"找不到模型：{MODEL}")

    cmd = [str(EXE), "-m", str(MODEL), "-p", prompt,
           "-W", str(size), "-H", str(size), "--steps", str(steps), "--cfg-scale", str(cfg),
           "-o", str(out)]
    if seed is not None:
        cmd += ["-s", str(seed)]

    # 用 DEVNULL 而非管道/日志文件：沙箱下管道 stdio 与 TEMP 子目录都可能被拒
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)

    return out if out.exists() and out.stat().st_size > 0 else None


def main() -> int:
    ap = argparse.ArgumentParser(description="本地文生图（stable-diffusion.cpp 封装）")
    ap.add_argument("--prompt", required=True, help="提示词（英文效果最好）")
    ap.add_argument("--preset", default="cover", choices=sorted(PRESETS), help="用途预设")
    ap.add_argument("--out", required=True, help="成品路径（可含中文）")
    ap.add_argument("--batch", type=int, default=1, help="生成几张（不同随机种子）")
    ap.add_argument("--seed", type=int, default=None, help="固定种子；batch>1 时作为起始种子")
    ap.add_argument("--steps", type=int, default=6, help="采样步数（LCM 模型 4~8 即可）")
    ap.add_argument("--size", type=int, default=512, help="生成分辨率（正方形边长）")
    ap.add_argument("--cfg", type=float, default=1.0, help="CFG（LCM 用 1.0）")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出结果，便于程序解析")
    args = ap.parse_args()

    preset = PRESETS[args.preset]
    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    workdir = Path(tempfile.gettempdir())   # 会话 TEMP 根目录：沙箱允许写，且是纯 ASCII
    run_id = uuid.uuid4().hex[:8]
    tmp_files: list[Path] = []
    results = []
    try:
        for i in range(max(1, args.batch)):
            seed = None if args.seed is None else args.seed + i
            raw = workdir / f"dsh_img_{run_id}_{i:02d}.png"
            tmp_files.append(raw)
            t0 = time.time()
            got = generate_one(args.prompt, seed, args.steps, args.size, args.cfg, raw)
            if got is None:
                results.append(dict(index=i, ok=False, seconds=round(time.time() - t0, 1),
                                    error="生成失败（提示词/显存/路径问题，可调低 --size 重试）"))
                continue

            im = Image.open(got).convert("RGB")
            w, h = im.width, im.height
            mode = preset["mode"]

            if mode == "cover_safe":
                # 中央方形安全区 + 两侧模糊背景（SOP：核心意象居中约 500x500，两侧只放背景/留白）
                W, H = preset["ratio"]
                canvas = Image.new("RGB", (W, H))
                bg = cover_resize(im, W, H).filter(ImageFilter.GaussianBlur(48))
                canvas.paste(ImageEnhance.Brightness(bg).enhance(0.72), (0, 0))
                side = min(H, im.height)
                canvas.paste(im.resize((side, side), Image.LANCZOS), ((W - side) // 2, 0))
                final = canvas
            elif mode == "soft":
                W, H = preset["ratio"]
                f = cover_resize(im, W, H).filter(ImageFilter.GaussianBlur(preset.get("blur", 6)))
                final = ImageEnhance.Brightness(f).enhance(preset.get("brightness", 0.85))
            else:
                final = im

            # batch>1 时按序号加后缀，避免互相覆盖
            target = out_path if args.batch == 1 else out_path.with_name(
                f"{out_path.stem}_{i:02d}{out_path.suffix}")
            q, kb = save_under(final, target, preset["limit_kb"], preset["quality"])
            results.append(dict(index=i, ok=True, path=str(target), size=f"{final.width}x{final.height}",
                                kb=kb, quality=q, seconds=round(time.time() - t0, 1)))

        if args.json:
            log(json.dumps(dict(preset=args.preset, prompt=args.prompt, results=results),
                           ensure_ascii=False, indent=2))
        else:
            for r in results:
                if r["ok"]:
                    log(f"OK   {r['path']}  {r['size']}  {r['kb']} KB  q={r['quality']}  {r['seconds']}s")
                else:
                    log(f"FAIL #{r['index']}  {r['error']}")
        return 0 if any(r["ok"] for r in results) else 1
    finally:
        for f in tmp_files:
            try:
                f.unlink()
            except OSError:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
