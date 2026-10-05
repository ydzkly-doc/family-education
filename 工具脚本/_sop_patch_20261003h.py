# -*- coding: utf-8 -*-
"""一次性补丁 H：条目录的"工作区"与"逐字稿"两处 SOP 缺口（2026-10-03 实测踩到）。

① **三个下划线工作区要"建条目录时就一起建"**——
   12 条稿子全写完才发现条目录里只有那个 .md，`_素材/`／`_成品/`／`_过程文件/` 全缺
   （用户对照旧系列一眼看出来）。SOP 的「目录结构」画了结构图，但**没写"什么时候建"**。

② **`_文案.txt` 是管道的产物，写稿阶段没有它是正常的**——
   用户看到旧条目录里有这个文件、新目录里没有，会以为漏了。
   它由 `video_make.py --md` 在**合成时**自动抽；写稿阶段想看就得手动跑重抽脚本。
   ⛔ 不能手改（是 MD 的派生物），且**改完口播必须重抽**（否则 `--script` 用旧稿、不报错）。

用法：
    PY="C:/Users/ZhuanZ/.workbuddy/binaries/python/versions/3.13.12/python.exe"
    "$PY" 工具脚本/_sop_patch_20261003h.py --dry-run
    "$PY" 工具脚本/_sop_patch_20261003h.py
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
("H1 建条目录时就建三个工作区", """> - 目录前缀 = **发布序**，**按名字排序就是发布顺序**。""",
 """> - 目录前缀 = **发布序**，**按名字排序就是发布顺序**。
>
> ⛔⭐⭐ **建条目录的那一刻，就把 `_素材/`／`_成品/`／`_过程文件/` 三个下划线区一起建好**
> （2026-10-03 实测踩到：12 条稿子全写完才发现条目录里**只有那个 .md**，三个工作区全缺，后补一轮）。
> · 📌 判据：**写完一条稿，条目录里应该是 1 个 md ＋ 1 个 txt ＋ 3 个 `_` 目录**，少一个就是没建齐。
> · 💡 **每个工作区放一份 `说明.txt`**：① 空目录 git 不跟踪，放个真文件才留得住；
>   ② 这三个目录是"拍摄的人／合成的人"第一眼看的地方，把要点写在那儿最省事
>   （`_素材/` 写拍摄规范、`_成品/` 写交付物与合成命令、`_过程文件/` 写哪几样核对时要用）。""", 1),

("H2 逐字稿 txt 是管道产物", """2. **逐字稿**：**不用手工抽**——`--md` 会自动从「一、口播文案」抽成 `<文案名>_文案.txt`（一行一句、剥掉方括号提示）。""",
 """2. **逐字稿**：**不用手工抽**——`--md` 会自动从「一、口播文案」抽成 `<文案名>_文案.txt`（一行一句、剥掉方括号提示）。
   > ⚠️ **它是"管道的产物"，所以写稿阶段条目录里没有它，是正常的**（首次合成时才出现）——
   > 2026-10-03 实测：用户对照旧系列发现新目录少一个文件，以为漏了。
   > → **想提前看一眼**（推荐：写完稿就抽一次，早发现"上屏句和口播对不上"）：
   >   `PY 工具脚本/重抽逐字稿_refresh_script.py <文案.md 或目录>`
   > → ⛔ **不要手工编辑它**（它是 MD 的派生物，手改必然再次失同步）；
   > → ⛔ **改完口播必须重抽一遍**——否则哪天直接 `--script 文案.txt`，用的就是**旧稿，而且不会报错**。""", 1),
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
