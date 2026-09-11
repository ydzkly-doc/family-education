#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
工作区过程文件过期扫描（只读，绝不删除）

用途：随时间推移，备份/归档/候选/预览类目录会不断累积。本脚本按"可重建性 + 时效"
      自动分级，给出建议保留天数与逾期提示，帮助定期清理。

用法：
  # 只读扫描，输出报告（默认）
  python 工具脚本/过程文件过期扫描_scan_stale.py

  # 指定保留天数（覆盖默认策略）
  python 工具脚本/过程文件过期扫描_scan_stale.py --keep-days A=7,B=14,C=30

  # 输出 markdown 报告到文件
  python 工具脚本/过程文件过期扫描_scan_stale.py --out _档案/报告/00_过程文件扫描_20260911.md

  # 列出某类的完整路径（供人工圈选后另行删除）
  python 工具脚本/过程文件过期扫描_scan_stale.py --list A

安全：本脚本只读不写（除 --out 指定的报告），不调用任何删除操作。
"""
import argparse
import datetime
import os
import sys

# ---- 过期策略：类别 -> (默认保留天数, 说明, 具体目录名模式) ----
# 判定原则：越"可重建"保留越短；越含"素材/提示词资产"保留越长。
POLICY = {
    "A": (7,    "完全可重建（预览页等，脚本随时重建）",
           ["_预览/"]),
    "B": (14,   "一次性快照（修复前备份，验证通过后即失效）",
           ["_backup*/", "_备份/"]),
    "C": (14,   "素材类（含可复用提示词与参数）",
           ["_封面候选*/", "_过程文件/", "_未采用*/", "_原始*/", "_归档*/"]),
    "D": (None, "长期归档（报告、长期资产，不自动过期）",
           ["_档案/", "_资产/"]),
}

# 目录名前缀 -> 类别
PREFIX_CAT = {
    "_预览": "A",
    "_backup": "B", "_备份": "B",
    "_封面候选": "C", "_过程文件": "C", "_未采用": "C", "_原始": "C", "_归档": "C",
    "_档案": "D", "_资产": "D",
}

SKIP_DIRS = {".git", ".workbuddy", "__pycache__", "node_modules"}


def classify(name):
    for pre, cat in PREFIX_CAT.items():
        if name.startswith(pre):
            return cat
    return None


def collect(base):
    """收集最外层的过程类目录（跳过嵌套，避免重复统计）。"""
    found = []
    for root, dirs, _ in os.walk(base):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        cat = classify(os.path.basename(root))
        if cat:
            found.append((root, cat))
    # 去嵌套：只保留最外层
    outer = []
    for d, cat in sorted(found, key=lambda x: len(x[0])):
        if not any(d.startswith(o + os.sep) for o, _ in outer):
            outer.append((d, cat))
    return outer


def stat_dir(root):
    size = 0
    cnt = 0
    newest = 0.0
    for r, _, files in os.walk(root):
        for f in files:
            p = os.path.join(r, f)
            try:
                st = os.stat(p)
                size += st.st_size
                cnt += 1
                newest = max(newest, st.st_mtime)
            except OSError:
                pass
    return size, cnt, newest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=".", help="工作区根目录（默认当前目录）")
    ap.add_argument("--keep-days", default="", help="覆盖保留天数，如 A=7,B=14,C=30")
    ap.add_argument("--out", default="", help="输出 markdown 报告到该路径")
    ap.add_argument("--list", default="", help="列出指定类别(A/B/C/D)的完整路径")
    ap.add_argument("--quiet", action="store_true", help="只输出汇总")
    ap.add_argument("--brief", action="store_true",
                    help="简报模式：只列具体文件夹名 + 建议动作（供定期扫描用）")
    args = ap.parse_args()

    # 解析覆盖
    policy = {k: list(v) for k, v in POLICY.items()}
    if args.keep_days:
        for part in args.keep_days.split(","):
            if "=" in part:
                k, v = part.split("=", 1)
                k = k.strip().upper()
                if k in policy:
                    try:
                        policy[k][0] = int(v)
                    except ValueError:
                        pass

    base = os.path.abspath(args.base)
    now = datetime.datetime.now()
    rows = []
    for d, cat in collect(base):
        size, cnt, newest = stat_dir(d)
        age = (now - datetime.datetime.fromtimestamp(newest)).days if newest else -1
        keep = policy[cat][0]
        expired = (keep is not None and age >= keep)
        rows.append({
            "path": os.path.relpath(d, base),
            "cat": cat,
            "size": size,
            "cnt": cnt,
            "age": age,
            "keep": keep,
            "expired": expired,
        })

    # --brief 模式：只列具体文件夹名 + 建议动作
    if args.brief:
        total = sum(r["size"] for r in rows)
        exp = [r for r in rows if r["expired"]]
        print(f"过程类目录共 {len(rows)} 个 / {total/1024/1024:.1f} MB；"
              f"超期 {len(exp)} 个 / {sum(r['size'] for r in exp)/1024/1024:.1f} MB")
        print()
        print("【超期 · 建议清理】" if exp else "【超期 · 无】目前没有超期文件夹，本周无需清理。")
        for r in sorted(exp, key=lambda x: -x["size"]):
            print(f"  - {r['path']}    [{r['cat']}] {r['size']/1024/1024:.2f}M · {r['age']}天")
        print()
        print("【各类占用（未超期也列出，便于掌握体量）】")
        for cat in sorted(policy):
            sub = [r for r in rows if r["cat"] == cat]
            if not sub:
                continue
            kd, pats = policy[cat][0], policy[cat][2]
            kd_txt = f"{kd}天" if kd is not None else "不过期"
            late = [r for r in sub if r["expired"]]
            print(f"  {cat} 类（{'、'.join(pats)}，保留{kd_txt}）：{len(sub)} 个 / "
                  f"{sum(r['size'] for r in sub)/1024/1024:.1f}M"
                  + (f"，其中超期 {len(late)} 个" if late else ""))
        return

    # --list 模式
    if args.list:
        cat = args.list.strip().upper()
        hit = [r for r in rows if r["cat"] == cat]
        for r in sorted(hit, key=lambda x: -x["size"]):
            print(os.path.join(base, r["path"]))
        print(f"\n共 {len(hit)} 个（{sum(r['size'] for r in hit)/1024/1024:.1f} MB）", file=sys.stderr)
        return

    # 汇总
    total_size = sum(r["size"] for r in rows)
    exp = [r for r in rows if r["expired"]]
    exp_size = sum(r["size"] for r in exp)

    lines = []
    lines.append("# 工作区过程文件扫描报告（只读）")
    lines.append("")
    lines.append(f"> 扫描时间：{now.strftime('%Y-%m-%d %H:%M')}　根目录：`{base}`")
    lines.append("> **本报告只读生成，未删除或移动任何文件。**")
    lines.append("")

    # ---- 最前面：直接给出「该清哪些文件夹」 ----
    lines.append("## 结论（先看这里）")
    lines.append("")
    lines.append(f"过程类目录共 **{len(rows)}** 个、合计 **{total_size/1024/1024:.1f} MB**；"
                 f"其中**已超期 {len(exp)} 个（{exp_size/1024/1024:.1f} MB）**。")
    lines.append("")
    if exp:
        lines.append("### 建议清理的文件夹（已超期）")
        lines.append("")
        lines.append("| 具体文件夹 | 类别 | 体积 | 已放置 |")
        lines.append("|---|---|---|---|")
        for r in sorted(exp, key=lambda x: -x["size"]):
            lines.append(f"| `{r['path']}` | {r['cat']} | {r['size']/1024/1024:.2f}M | {r['age']} 天 |")
        lines.append("")
    else:
        lines.append("**目前没有任何超期文件夹，本周无需清理。**")
        lines.append("")

    # ---- 各目录名模式 → 类别对照（解决"不知道 A 类是什么"） ----
    lines.append("## 类别对照（各目录名模式及其保留期）")
    lines.append("")
    lines.append("| 类 | 对应目录名 | 含义 | 建议保留 |")
    lines.append("|---|---|---|---|")
    for k, v in sorted(policy.items()):
        kd, desc, pats = v[0], v[1], v[2]
        kd_txt = f"{kd} 天" if kd is not None else "不过期"
        lines.append(f"| {k} | {'、'.join('`'+p+'`' for p in pats)} | {desc} | {kd_txt} |")
    lines.append("")

    for cat in sorted(policy):
        sub = [r for r in rows if r["cat"] == cat]
        if not sub:
            continue
        kd, desc = policy[cat][0], policy[cat][1]
        lines.append(f"## {cat} 类明细 · {desc}　（{len(sub)} 个 / {sum(r['size'] for r in sub)/1024/1024:.1f} MB）")
        lines.append("")
        lines.append("| 状态 | 体积 | 文件 | 最后修改 | 路径 |")
        lines.append("|---|---|---|---|---|")
        for r in sorted(sub, key=lambda x: -x["size"]):
            if r["keep"] is None:
                flag = "长期"
            elif r["expired"]:
                flag = f"**超期** ({r['age']}天)"
            else:
                flag = f"保留 ({r['age']}/{r['keep']}天)"
            lines.append(
                f"| {flag} | {r['size']/1024/1024:.2f}M | {r['cnt']} | {r['age']}天前 | `{r['path']}` |"
            )
        lines.append("")

    lines.append("## 下一步")
    lines.append("")
    lines.append("1. 圈选上表中确认可清的项（A 类通常可全清，B 类确认对应修复已验证通过后可清）")
    lines.append("2. 按 SOP 三步安全清理法执行：`send2trash` 回收站 + 分批 ≤10 项 + 逐批核对")
    lines.append("3. 清理前先 `git commit` 一次，让删除可回滚")
    lines.append("4. 清理后重跑 `系列发布全套自检_selfcheck.py` 确认正式成果零影响")
    lines.append("")

    report = "\n".join(lines)

    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"✓ 报告已写入：{args.out}")
        print(f"  目录 {len(rows)} 个 / {total_size/1024/1024:.1f} MB；超期 {len(exp)} 个 / {exp_size/1024/1024:.1f} MB")
    else:
        print(report)

    if not args.quiet:
        # 提示超期项
        if exp:
            print()
            print("=== 超期项（可优先清理）===")
            for r in sorted(exp, key=lambda x: -x["size"])[:15]:
                print(f"  {r['size']/1024/1024:>6.2f}M  {r['age']:>3}天  [{r['cat']}] {r['path']}")
            if len(exp) > 15:
                print(f"  ... 另 {len(exp)-15} 项")
        else:
            print()
            print("=== 暂无超期项 ===")


if __name__ == "__main__":
    main()
