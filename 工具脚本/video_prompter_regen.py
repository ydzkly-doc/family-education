# -*- coding: utf-8 -*-
"""按 _prompter_args.json 批量重生成「二、提词器文案」。

用法：
    video_prompter_regen.py <系列目录> [序号…] [--check]

    --check  只比对、不写入（把 gen_prompter 的 --check 透传下去，用来核"提词器与口播是否同步"）
"""
import io
import json
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

PY = r"C:/Users/ZhuanZ/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
ROOT = r"D:/个人资料/家庭教育"


def main():
    argv = sys.argv[1:]
    check = "--check" in argv
    argv = [a for a in argv if a != "--check"]
    series = argv[0] if argv else ""
    want = argv[1:]
    if not series:
        raise SystemExit(__doc__)
    args_path = os.path.join(series, "_prompter_args.json")
    items = json.load(io.open(args_path, encoding="utf-8"))
    ok = bad = 0
    for it in items:
        seq = it["file"][:2]
        if want and seq not in want:
            continue
        md = os.path.join(series, it["file"])
        if not os.path.exists(md):
            print(f"[skip] 缺文件 {it['file']}")
            continue
        cmd = [PY, os.path.join(ROOT, "工具脚本", "gen_prompter.py"), md,
               "--cuts", "||".join(it["cuts"]),
               "--titles", "||".join(it["titles"])]
        if check:
            cmd.append("--check")
        p = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        tail = (p.stdout or "").strip().splitlines()
        head = tail[0] if tail else ""
        if p.returncode == 0:
            ok += 1
            print(f"[OK] {seq}  {head}")
        else:
            bad += 1
            print(f"[!!] {seq}  失败：")
            for ln in tail[-6:]:
                print("      " + ln)
    print(f"\n{'核对' if check else '生成'}：成功 {ok} ／ 失败 {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
