#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
expert_avatar_resize.py —— 把 ImageGen 产出的专家头像压到专家包规范尺寸

为什么需要它
    expert-manager 的头像规范要求：**512x512 px、PNG/JPG、单张 <= 500KB**。
    而 ImageGen 直接产出的是 1024x1024、动辄 1.5~2MB，**必然超标**。
    官方脚本不管这一步，所以每次建专家包都得手动压一次 —— 本脚本固化它。

用法
    python 工具脚本/expert_avatar_resize.py <图片路径> [--out <输出路径>] [--max-kb 500]
    python 工具脚本/expert_avatar_resize.py <专家包目录>          # 自动处理 avatars/ 下所有超标图片

    不给 --out 时**原地覆盖**（原图备份到系统临时目录，除非加 --no-backup）。

示例
    python 工具脚本/expert_avatar_resize.py \
        "$EXPDIR/my-expert/avatars/expert.png"

    python 工具脚本/expert_avatar_resize.py "$EXPDIR/my-expert"   # 整包

注意
    - 只用 Pillow（默认 venv 已装）。
    - ⚠️ **备份不落在专家包内**——否则会被 `package_expert.py` 打进 zip，白白膨胀。
      原图备份统一放到 `%TEMP%/expert_avatar_backup/`，路径会打印出来。
    - 压缩策略：先等比缩放并中心裁成正方形 -> 转 RGB -> 从高质量往下降，取第一个达标档。
"""
import argparse
import os
import shutil
import sys
import tempfile

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

try:
    from PIL import Image
except ImportError:
    print("⛔ 缺少 Pillow。请先装：")
    print('   "C:/Users/ZhuanZ/.workbuddy/binaries/python/envs/default/Scripts/pip.exe" install pillow')
    sys.exit(2)

SIZE = 512
EXTS = (".png", ".jpg", ".jpeg", ".webp")
BACKUP_DIR = os.path.join(tempfile.gettempdir(), "expert_avatar_backup")


def kb(path):
    return os.path.getsize(path) / 1024.0


def to_square(img, size=SIZE):
    """等比缩放 + 中心裁成正方形。"""
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    img = img.crop((left, top, left + side, top + side))
    return img.resize((size, size), Image.LANCZOS)


def compress(src, out, max_kb=500):
    """压到 <= max_kb，返回 (成功?, 最终KB, 用的档位说明)"""
    img = Image.open(src)
    img = img.convert("RGB") if img.mode not in ("RGB", "RGBA") else img
    sq = to_square(img)

    # 从好到差依次尝试；PNG 用 optimize，仍超标就退 JPEG
    attempts = [
        ("PNG optimize", lambda p: sq.save(p, "PNG", optimize=True)),
        ("PNG optimize + 减色", lambda p: sq.convert("P").convert("RGB").save(p, "PNG", optimize=True)),
        ("JPG q=88", lambda p: sq.save(p, "JPEG", quality=88, optimize=True)),
        ("JPG q=80", lambda p: sq.save(p, "JPEG", quality=80, optimize=True)),
        ("JPG q=70", lambda p: sq.save(p, "JPEG", quality=70, optimize=True)),
    ]

    for label, fn in attempts:
        tmp = out + ".tmp"
        fn(tmp)
        size_kb = kb(tmp)
        if size_kb <= max_kb:
            os.replace(tmp, out)
            return True, size_kb, label
        os.remove(tmp)

    # 全都不行：直接落最后档，如实返回
    fn(out)
    return False, kb(out), "JPG q=70（仍超标）"


def process(path, out=None, max_kb=500, no_backup=False):
    if kb(path) <= max_kb:
        print(f"  ✅ 已达标 {kb(path):.0f} KB，跳过：{os.path.basename(path)}")
        return 0

    original_kb = kb(path)
    target = out or path

    if out is None and not no_backup:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        backup = os.path.join(BACKUP_DIR, os.path.basename(path))
        shutil.copy2(path, backup)
        print(f"  📦 原图已备份到（包外）-> {backup}")

    ok, final_kb, how = compress(path, target, max_kb)
    flag = "✅" if ok else "⚠️"
    print(f"  {flag} {os.path.basename(path)}：{original_kb:.0f} KB -> {final_kb:.0f} KB"
          f"（512x512，{how}）")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(
        description="把专家头像压到 512x512 / <=500KB（expert-manager 头像规范）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("示例")[0],
    )
    ap.add_argument("target", help="图片文件，或专家包目录（自动扫 avatars/）")
    ap.add_argument("--out", default=None, help="输出路径（默认原地覆盖，会留 .orig 备份）")
    ap.add_argument("--max-kb", type=int, default=500, help="大小上限 KB（默认 500）")
    ap.add_argument("--no-backup", action="store_true", help="原地覆盖时不留备份")
    args = ap.parse_args()

    target = os.path.abspath(args.target)
    if not os.path.exists(target):
        print(f"⛔ 路径不存在：{target}")
        return 2

    print("=" * 64)
    print("专家头像压缩（512x512 / <=500KB）")
    print("=" * 64)

    rc = 0
    if os.path.isdir(target):
        avatars = os.path.join(target, "avatars")
        if not os.path.isdir(avatars):
            print(f"⛔ 目录下没有 avatars/：{target}")
            return 2
        files = [os.path.join(avatars, f) for f in sorted(os.listdir(avatars))
                 if f.lower().endswith(EXTS) and not f.lower().endswith(".orig.png")]
        if not files:
            print("  （没有图片）")
            return 0
        print(f"  专家包：{target}")
        print(f"  待处理 {len(files)} 张\n")
        for f in files:
            rc |= process(f, args.out, args.max_kb, args.no_backup)
    else:
        if not args.target.lower().endswith(EXTS):
            print(f"⛔ 不是图片文件：{target}")
            return 2
        rc = process(target, args.out, args.max_kb, args.no_backup)

    print()
    print("✅ 完成" if rc == 0 else "⚠️ 有文件仍超标，请人工确认")
    print("   校验整包：python3 scripts/validate_expert.py <expert-dir>")
    return rc


if __name__ == "__main__":
    sys.exit(main())
