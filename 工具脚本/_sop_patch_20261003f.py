# -*- coding: utf-8 -*-
"""一次性补丁 F：E-1 机械改名（第二批残留）。

第一遍（补丁 E）清掉了小节标题与主要引用；这一遍清**剩余 4 处**——
它们都是**正文里的引用／表格**，不是标题，所以第一遍的正则没覆盖到：
  · 3.16 引外部评测原话里的「二、口播文案」
  · 「金句 ≠ 封面」那条里的「四、上屏方案 → `### 封面`」
  · 分工表两行（`| **二、口播文案** |` ／ `| **三、提词器文案** |`）

⛔ **故意不动的一处**：`## 二、口播文案`（在"脚本原来写死了…"那句里）——
   那是**历史事实**（当时写死的就是 `二、`），改了反而不准。

用法：
    PY="C:/Users/ZhuanZ/.workbuddy/binaries/python/versions/3.13.12/python.exe"
    "$PY" 工具脚本/_sop_patch_20261003f.py --dry-run
    "$PY" 工具脚本/_sop_patch_20261003f.py
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
("F1 3.16 引评测·口播文案", """> 它看到的是「**二、口播文案**」（**机器源，出镜者根本不看那一段**），而「二、提词器文案」本来就是整句。""",
 """> 它看到的是「**一、口播文案**」（**机器源，出镜者根本不看那一段**），而「二、提词器文案」本来就是整句。""", 1),

("F2 金句≠封面·引用", """封面另有**三条硬规则**，见「四、上屏方案 → `### 封面`」。""",
 """封面另有**三条硬规则**，见「三、上屏方案 → `### 封面`」。""", 1),

("F3 分工表·口播文案", """> | **二、口播文案** | **机器**——管道 `md_spec.extract_script()` 从它抽逐字稿""",
 """> | **一、口播文案** | **机器**——管道 `md_spec.extract_script()` 从它抽逐字稿""", 1),

("F4 分工表·提词器文案", """> | **三、提词器文案** | **人**——⭐ **出镜者排练、录制、审阅的唯一版本**""",
 """> | **二、提词器文案** | **人**——⭐ **出镜者排练、录制、审阅的唯一版本**""", 1),
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
        print("\n=== 需要处理 ===")
        return 1
    print("\n全部通过 ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
