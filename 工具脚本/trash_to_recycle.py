#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
trash_to_recycle.py —— 把文件/目录安全地送进 Windows 回收站，并核实条目。

为什么要它：本项目多次要"删文件"，而安全策略会拦 PowerShell 的
Add-Type Microsoft.VisualBasic / New-Object Shell.Application，
且中文路径极易出问题。本脚本把已踩通的路线固化下来。

用法（必须用带 send2trash+pywin32 的 venv 跑）：
    PY=C:/Users/ZhuanZ/.workbuddy/binaries/python/envs/default/Scripts/python.exe

    "$PY" trash_to_recycle.py <路径1> [路径2 ...]            # 送回收站
    "$PY" trash_to_recycle.py <路径> --dry-run               # 只看会删什么
    "$PY" trash_to_recycle.py --list [--since 60]            # 只列最近条目，不删

关键坑（务必记住）：
  1. ⚠️ 核实回收站条目必须扫「**被删文件所在盘**」的 $Recycle.Bin。
     D 盘删的东西**不在** C:\\$Recycle.Bin —— 只扫 C 盘会误判成"没进回收站"。
  2. ⚠️ send2trash 可能抛 FileNotFoundError / OSError -2147024809，
     但其实**已经成功**进回收站。→ 一律以"回收站是否出现该条目"为最终判据，
     ⛔ 不要因为异常就改走 os.remove() 直删（直删不可恢复）。
  3. 不加 pywin32，send2trash 会回退 legacy 实现对中文路径报 Errno 3。
  4. 只兼容 Windows。
"""
import argparse
import datetime
import glob
import os
import struct
import sys
import time

IS_WIN = sys.platform.startswith("win")


# ---------------------------------------------------------------- 回收站读取
def _drives():
    if not IS_WIN:
        return []
    out = []
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        root = f"{letter}:\\"
        if os.path.exists(root):
            out.append(root)
    return out


def _parse_i(path):
    """解析回收站 $I 元数据文件 → 原始路径（UTF-16LE）"""
    try:
        with open(path, "rb") as f:
            data = f.read()
        if len(data) < 24:
            return ""
        n = struct.unpack_from("<I", data, 16)[0]
        return data[24:24 + n * 2].decode("utf-16-le", "ignore").rstrip("\x00")
    except Exception:
        return ""


def scan_recycle(since_seconds=None):
    """
    扫所有盘的回收站，返回 [(mtime, i_file, orig_path, drive)]。
    since_seconds 给定时只返回该时间窗内的条目。
    """
    now = time.time()
    rows = []
    for dr in _drives():
        rb = os.path.join(dr, "$Recycle.Bin")
        if not os.path.isdir(rb):
            continue
        try:
            sids = os.listdir(rb)
        except PermissionError:
            continue
        for sid in sids:
            sid_dir = os.path.join(rb, sid)
            if not os.path.isdir(sid_dir):
                continue
            for i_file in glob.glob(os.path.join(sid_dir, "$I*")):
                try:
                    mt = os.path.getmtime(i_file)
                except OSError:
                    continue
                if since_seconds is not None and now - mt > since_seconds:
                    continue
                rows.append((mt, i_file, _parse_i(i_file), dr))
    rows.sort(key=lambda r: r[0])
    return rows


# ---------------------------------------------------------------- 主流程
def cmd_list(args):
    rows = scan_recycle(args.since * 60 if args.since else None)
    if not rows:
        print("  没有符合条件的回收站条目")
        return 0
    for mt, _i, orig, _dr in rows:
        ts = datetime.datetime.fromtimestamp(mt).strftime("%Y-%m-%d %H:%M:%S")
        print(f"  [{ts}] {orig}")
    print(f"  ---- 共 {len(rows)} 条")
    return 0


def cmd_trash(args):
    targets = [os.path.abspath(p) for p in args.paths]
    missing = [p for p in targets if not os.path.exists(p)]
    if missing:
        print("❌ 以下路径不存在：")
        for p in missing:
            print("   " + p)
        return 2

    # 1) 清单
    print("=" * 64)
    print("【1】将送回收站的内容")
    print("=" * 64)
    total = 0
    n_files = 0
    for t in targets:
        if os.path.isfile(t):
            s = os.path.getsize(t)
            total += s
            n_files += 1
            print(f"  {s:>12,}  {t}")
        else:
            sub = 0
            for d, _sub, fs in os.walk(t):
                for f in fs:
                    try:
                        sub += os.path.getsize(os.path.join(d, f))
                        n_files += 1
                    except OSError:
                        pass
            total += sub
            print(f"  {sub:>12,}  {t}\\  (目录)")
    print(f"  ---- {len(targets)} 个对象，{n_files} 个文件，{total / 1048576:.1f} MB")

    if args.dry_run:
        print("\n--dry-run：未执行任何删除。")
        return 0

    # 2) 基线
    before = {r[1] for r in scan_recycle()}
    print(f"\n【2】删除前回收站条目数（全盘）：{len(before)}")

    # 3) 执行
    print("\n【3】送回收站")
    err = None
    if not IS_WIN:
        print("  ⚠️ 非 Windows 平台，尝试 gio trash")
        try:
            import shutil as _sh
            for t in targets:
                _sh.which("gio") and os.system(f'gio trash "{t}"')
        except Exception as e:  # noqa
            err = e
    else:
        try:
            from send2trash.win.modern import send2trash as st_modern
            print("  使用 IFileOperation（原生 Unicode）")
            for t in targets:
                st_modern(t)
            print("  调用完成")
        except Exception as e:
            err = e
            print(f"  ⚠️ 抛出异常：{type(e).__name__}: {e}")
            print("  （按纪律：无论抛什么，都以回收站条目为最终判据）")

    # 4) 判据
    print("\n【4】核实（最终判据 = 回收站条目，不看是否抛异常）")
    still = [p for p in targets if os.path.exists(p)]
    print(f"  原路径仍存在：{len(still)} / {len(targets)}" + ("  ✅" if not still else "  ❌"))
    for p in still:
        print("     " + p)

    after = scan_recycle()
    new = [r for r in after if r[1] not in before]
    print(f"  回收站新增条目：{len(new)}")
    for mt, _i, orig, dr in new:
        ts = datetime.datetime.fromtimestamp(mt).strftime("%H:%M:%S")
        print(f"     [{ts}] {orig}")

    ok = (not still) and len(new) > 0
    print()
    if ok:
        print("✅ 已进回收站，可恢复（回收站 → 右键还原）")
        return 0
    if err is not None:
        print("⚠️ 抛了异常且未在回收站找到条目 —— 请人工打开回收站确认后再决定下一步。")
        print("   ⛔ 不要再补一次删除，也不要用 os.remove() 直删。")
        return 1
    print("⚠️ 未在回收站找到新条目 —— 请人工确认（注意：要按被删文件所在盘去找）。")
    return 1


def main():
    ap = argparse.ArgumentParser(
        description="把文件/目录送进 Windows 回收站并核实条目",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("关键坑")[0],
    )
    ap.add_argument("paths", nargs="*", help="要删除的路径（文件或目录，可多个）")
    ap.add_argument("--dry-run", action="store_true", help="只列清单，不删")
    ap.add_argument("--list", action="store_true", help="只列回收站条目（配合 --since）")
    ap.add_argument("--since", type=int, default=0, metavar="分钟",
                    help="与 --list 配合：只看最近 N 分钟（默认全部）")
    args = ap.parse_args()

    if args.list:
        return cmd_list(args)
    if not args.paths:
        ap.print_help()
        return 0
    return cmd_trash(args)


if __name__ == "__main__":
    sys.exit(main())
