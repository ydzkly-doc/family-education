# -*- coding: utf-8 -*-
"""一次性补丁 G：自检清单补一句"提词器里没有标记"（2026-10-03）。

由来（这轮用户真的被卡了一下）：
    用户问「系列介绍既然合并到第一条视频了，那为什么在提词器文案中没有？」
    —— 其实**在**（提词器第 3 段末尾、最后一条金句之后），
    但**提词器里看不到任何 `【…】` 标记**（`gen_prompter` 按设计把行首标记剥掉），
    所以**搜"开头条／系列说明"永远搜不到** → 很容易误判成"漏了"。
    → 把这条**写进自检清单**，免得下一个系列再花一轮去查。

用法：
    PY="C:/Users/ZhuanZ/.workbuddy/binaries/python/versions/3.13.12/python.exe"
    "$PY" 工具脚本/_sop_patch_20261003g.py --dry-run
    "$PY" 工具脚本/_sop_patch_20261003g.py
    # 然后： "$PY" 工具脚本/expert_pack_sync.py video-script-studio
"""
import argparse
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

SOP = os.path.join(
    os.path.expanduser("~"),
    ".workbuddy", "plugins", "cache", "my-experts",
    "video-script-studio", "1.0.0", "agents", "video-script-studio.md")

PROTECT = ["通顺", "口语", "垫字", "电报腔", "念稿感", "拗口", "副词", "书面"]

R = [
("G1 自检·提词器里没有标记", """      开头条**没写成预告片**吧、结尾条**没写成汇报腔**吧？""",
 """      开头条**没写成预告片**吧、结尾条**没写成汇报腔**吧？
      ⚠️ **核的时候注意**：**提词器里没有任何 `【…】` 标记**（`gen_prompter` 按设计把行首标记剥掉，
      提词器只留"能直接念出口的话"）→ **开头条／结尾条那几句要"按位置核"**：
      **最后一条金句之后**（01 实测：提词器第 3 段末尾）。⛔ **别搜"开头条／系列说明"**——
      搜不到**不等于漏了**，搜到了才是问题（说明标记混进了提词器）。""", 1),
]


def norm(s: str) -> str:
    return (s.replace("\u201c", '"').replace("\u201d", '"')
             .replace("\u2018", "'").replace("\u2019", "'"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--file", default=SOP)
    a = ap.parse_args()

    t = io.open(a.file, encoding="utf-8").read()
    nt = norm(t)
    print(f"目标：{a.file}\n原始 {len(t)} 字符\n")

    problems = 0
    for label, old, new, exp in R:
        hit = [k for k in PROTECT if k in old]
        if hit:
            print(f"⛔ {label}：原文含保护词 {hit} —— 拒绝执行")
            problems += 1
            continue
        n = nt.count(norm(old))
        if n != exp:
            print(f"❌ {label}：命中 {n} 处（预期 {exp}）")
            problems += 1
            continue
        if a.dry_run:
            print(f"✅ {label}：命中 {n} 处")
            continue
        i = nt.find(norm(old))
        t = t[:i] + new + t[i + len(old):]
        nt = norm(t)
        print(f"✅ {label}：已替换")

    if not a.dry_run and not problems:
        io.open(a.file, "w", encoding="utf-8").write(t)
        print(f"\n已写入 {a.file}")

    if problems:
        return 1
    print("\n全部通过 ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
