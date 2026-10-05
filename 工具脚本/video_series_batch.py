# -*- coding: utf-8 -*-
"""系列批量：按 JSON 逐条「生成提词器 → 跑三项自检」，一次跑完一个批次。

为什么要有它：
    一个系列 10+ 条，每条都要 `gen_prompter` ＋ `video_script_check` ＋ `video_script_wrap_check`
    三条命令——手工敲 30+ 次，且 `--cuts/--titles` 里全是中文标点，**极易在 shell 里被吃掉**。
    → 参数落成 JSON（可复查、可重跑），脚本一次跑完并打印汇总。

参数文件（默认 `视频号文案/_过程文件/_prompter_args.json`）：
    [
      {"file": "01_xxx/视频号文案_01_….md",
       "cuts": ["第1段最后一句。", "第2段最后一句。"],
       "titles": ["第1段说明", "第2段说明", "第3段说明"]}
    ]
    ⚠️ `cuts` 数 = `titles` 数 − 1；每句必须是口播里**独占一行的一整句**。

用法：
    PY="C:/Users/ZhuanZ/.workbuddy/binaries/python/versions/3.13.12/python.exe"
    "$PY" 工具脚本/video_series_batch.py "公众号/改善你的亲子关系/视频号文案/_过程文件/_prompter_args.json"
    "$PY" 工具脚本/video_series_batch.py <json> --only 02 03     # 只跑指定条（按文件名前缀匹配）
"""
import argparse
import io
import json
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable
GEN = os.path.join(ROOT, "工具脚本", "gen_prompter.py")
CHK = os.path.join(ROOT, "工具脚本", "video_script_check.py")
WRAP = os.path.join(ROOT, "工具脚本", "video_script_wrap_check.py")


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("args_json")
    ap.add_argument("--only", nargs="*", default=None, help="只跑文件名以此开头的条")
    ap.add_argument("--skip-gen", action="store_true", help="只自检，不重生成提词器")
    a = ap.parse_args()

    base = os.path.dirname(os.path.abspath(a.args_json))
    items = json.load(io.open(a.args_json, encoding="utf-8"))

    bad = []
    for it in items:
        path = it["file"] if os.path.isabs(it["file"]) else os.path.join(base, it["file"])
        name = os.path.basename(path)
        if a.only and not any(name.startswith(p) for p in a.only):
            continue
        print("=" * 70)
        print(f"【{name}】")

        if not os.path.exists(path):
            print("  ❌ 文件不存在")
            bad.append(name)
            continue

        if not a.skip_gen:
            rc, out = run([PY, GEN, path, "--cuts", "||".join(it["cuts"]),
                           "--titles", "||".join(it["titles"])])
            print("  " + out.strip().replace("\n", "\n  ")[:600])
            if rc != 0:
                print("  ❌ gen_prompter 失败")
                bad.append(name)
                continue

        rc, out = run([PY, CHK, path])
        keep = [l for l in out.split("\n")
                if l.startswith("口播：") or l.startswith("时长：") or l.startswith("短句行占比")
                or "❌" in l or "✅ 硬指标" in l or "⚠️  [" in l]
        print("  " + "\n  ".join(keep[:14]))
        if rc != 0:
            bad.append(name)

        rc, out = run([PY, WRAP, path])
        tail = [l for l in out.split("\n") if "✅ 折行" in l or "❌" in l]
        print("  " + "\n  ".join(tail[:8]))
        if rc != 0:
            bad.append(name + "(折行)")

    print("=" * 70)
    if bad:
        print("⚠️ 需处理：" + "、".join(sorted(set(bad))))
        return 1
    print("✅ 本批全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
