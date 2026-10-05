#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文档路径巡检 —— 迁移/改名之后，检查**文档里手写的路径**有没有漏改。

为什么需要它（2026-09-30 立，实战踩出来的）
--------------------------------------------
2026-09-29 把 16 个内容系列从根目录移进 `公众号/` 时，批量替换脚本改的是**脚本里的引用**；
但**文档里手写的命令**（md 代码块里的 `--md "D:\\...\\孩子不上学了怎么办\\..."`）**没被规则命中**——
01–04 四条已发布文案的「四、视频合成方案」命令全都指向旧路径，**而且不会自己报错**，
只在**真的重跑那一刻**才炸（"找不到文件"）。

所以迁移后必须单独做两件事：
  ① **旧路径残留扫描**——`家庭教育\\` 后面**不跟新前缀**（公众号/学习计划/工具脚本/_）的，都是漏网的；
  ② **命令路径存在性验证**——换了前缀不等于对：把 md 里 `--md/--videos-dir/--out` 的路径抽出来，
     逐个查**文件/目录是否真实存在**。

用法
----
    PY="C:/Users/ZhuanZ/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
    "$PY" 工具脚本/check_doc_paths.py                  # 默认扫 公众号/
    "$PY" 工具脚本/check_doc_paths.py --root 学习计划    # 换目录
    "$PY" 工具脚本/check_doc_paths.py --quiet          # 只报问题

退出码：0＝干净（或仅有提示）；1＝发现旧路径残留或路径不存在。
"""
import argparse
import glob
import io
import os
import re
import sys

ROOT = r"D:/个人资料/家庭教育"
# 新结构前缀（`家庭教育\` 后面跟着这些＝正常的）
NEW_PREFIX = ("公众号", "学习计划", "工具脚本", "_")
SKIP_DIRS = ("_过程文件", "_备份", "_旧版本", "_档案", "_预览")
# ⚠️ 除精确名外，还要按**前缀**跳过带日期的快照目录（如 `_备份_更新前_20260918`、`_归档_废判据`）：
#   它们是历史快照，本就不该被要求"路径合规"，报出来只会让巡检永远显示"需要修复"。
SKIP_DIR_PREFIXES = ("_备份_", "_归档_")


def scan_stale(root):
    """扫旧路径残留：家庭教育\\ + 非新前缀"""
    stale = []
    # ⚠️ 判断前先把 JSON 里**成对转义**的反斜杠归一成单个再匹配。
    #    不能用 `\\{1,2}` 之类的写法：量词会回溯——贪婪吃两个反斜杠后断言失败、退回吃一个，
    #    于是已修好的 `家庭教育\\公众号\\…` 又被判成残留（2026-09-30 实测 77 条误报）。
    pat = re.compile(r"家庭教育\\(?!公众号|学习计划|工具脚本|_)")
    for dirpath, dirnames, files in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d not in SKIP_DIRS and not d.startswith(SKIP_DIR_PREFIXES)]
        for f in files:
            if not f.lower().endswith((".md", ".py", ".txt", ".json")):
                continue
            p = os.path.join(dirpath, f)
            try:
                t = io.open(p, encoding="utf-8", errors="ignore").read()
            except Exception:
                continue
            for i, line in enumerate(t.split("\n"), 1):
                probe = line.replace("\\\\", "\\")        # JSON 的 `\\` → `\`，只用于判断
                if pat.search(probe):
                    stale.append((os.path.relpath(p, root), i, line.strip()[:96]))
    return stale


def check_commands(root):
    """验证 md 里 --md/--videos-dir/--out 的路径是否存在"""
    bad, total = [], 0
    for p in glob.glob(os.path.join(root, "**", "*.md"), recursive=True):
        if any(s in p for s in SKIP_DIRS):
            continue
        try:
            t = io.open(p, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        for label, pat in (("--md", r'--md "([^"]+)"'),
                           ("--videos-dir", r'--videos-dir "([^"]+)"'),
                           ("--out", r'--out "([^"]+)"')):
            for val in re.findall(pat, t):
                v = val.replace("\\", "/")
                if not os.path.isabs(v):
                    continue
                total += 1
                target = os.path.dirname(v) if label == "--out" else v
                if not os.path.exists(target):
                    bad.append((os.path.relpath(p, root), label, val))
    return bad, total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="公众号", help="要巡检的目录（相对工作空间根）")
    ap.add_argument("--quiet", action="store_true", help="只报问题")
    a = ap.parse_args()

    root = os.path.join(ROOT, a.root)
    if not os.path.isdir(root):
        print(f"❌ 目录不存在：{root}")
        return 1

    if not a.quiet:
        print("=" * 72)
        print(f"文档路径巡检：{a.root}/")
        print("=" * 72)

    stale = scan_stale(root)
    bad, total = check_commands(root)

    if not a.quiet:
        print(f"\n① 旧路径残留（`家庭教育\\` 后不跟新前缀）：{len(stale)} 条")
        for f, i, line in stale[:10]:
            print(f"    · {f}:{i}")
            print(f"      {line}")
        if len(stale) > 10:
            print(f"    …（共 {len(stale)} 条）")

        print(f"\n② 命令路径存在性：共查 {total} 个绝对路径，不存在 {len(bad)} 个")
        for f, label, val in bad[:10]:
            print(f"    ❌ {f}  {label}\n       {val}")

    if not stale and not bad:
        if not a.quiet:
            print("\n✅ 干净：无旧路径残留，命令里的路径全部存在")
        return 0

    if stale or bad:
        print("\n⚠️ 需要修复（上面的清单）")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
