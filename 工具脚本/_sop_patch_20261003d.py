# -*- coding: utf-8 -*-
"""一次性补丁 D：结构标记必须"独占一行"（2026-10-03 实测立）。

由来（这轮真踩到）：
    `【系列·说明】`／`【引流·可选】`／`【合集·过渡】` 这三个标记，
    **提词器脚本是按"行首是不是【"整行过滤的**（`gen_prompter.extract_spoken`）——
    写成 `【引流·可选】更细的那几个问法…` **同一行** → **整行被丢掉**
    → **提词器里没有这句 → 出镜者直接漏念**（且 `video_script_check.py` 的字数/时长**也跟着漏算**）。
    ⭐ 存量 01~06 **全都**是"标记独占一行"，所以一直没暴露；本轮新写的 01 条写成了行内才踩到。
    → 这条**必须写进 SOP**（它属于"静默失败"那一类：不报错、只是那句没了）。

用法：
    PY="C:/Users/ZhuanZ/.workbuddy/binaries/python/versions/3.13.12/python.exe"
    "$PY" 工具脚本/_sop_patch_20261003d.py --dry-run
    "$PY" 工具脚本/_sop_patch_20261003d.py
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
("P11 结构标记独占一行", """- 金句用【★金句】/【☆】单独标出；拍摄提示**素人友好、宁少勿多**（**≤6 处**）：【停一下】【这句放慢】【看镜头】【语气松下来】等，**只标停顿/放慢/看镜头**，不指挥复杂表情。""",
"""- 金句用【★金句】/【☆】单独标出；拍摄提示**素人友好、宁少勿多**（**≤6 处**）：【停一下】【这句放慢】【看镜头】【语气松下来】等，**只标停顿/放慢/看镜头**，不指挥复杂表情。
- ⛔⭐⭐ **所有 `【…】` 结构标记必须"独占一行"，台词另起一行**（2026-10-03 实测立）——
  `【系列·说明】`／`【引流·可选】`／`【合集·过渡】`（以及可选的 `【★金句】`／`【☆】`）都算。
  **为什么**：提词器脚本 `gen_prompter.extract_spoken()` 是**按"行首是不是【"整行过滤**的——
  写成 `【引流·可选】更细的那几个问法…` **同一行** → **整行被丢掉**
  → **提词器里就没有这句 → 出镜者直接漏念**（不报错、静默发生），
  同时 `video_script_check.py` 的**字数/时长也跟着漏算**。
  → ✅ **正解**：`【引流·可选】` 单独一行 ＋ **空一行** ＋ 台词单独一行（存量 01~06 全是这么写的）。
  → 🔧 **自检已加拦截**：写成同一行会直接报 ❌「结构标记写成了「标记＋台词」同一行」。
- ⚠️ **与"拍摄提示内嵌"的区别**：`【停一下】【看镜头】` 这类**念法提示**是**给你看的**，本来就不进提词器；
  结构标记行里的**台词是必须念的**——两者别混（混了就漏念）。""", 1),
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
