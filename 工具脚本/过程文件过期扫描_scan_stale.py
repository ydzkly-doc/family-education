#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
工作区过程文件过期扫描（只读，绝不删除）

用途：随时间推移，备份/归档/候选/预览类目录会不断累积。本脚本按"可重建性 + 时效"
      自动分级，给出建议保留天数与逾期提示，帮助定期清理。

判龄口径（⛔ 不可改）：
  **只看"文件真实最后修改时间"（st_mtime），目录自身的时间一概不看。**
  目录 mtime 会因子项增删被改写，既不代表内容新旧，也会随无关操作漂移。
  · 普通过程目录 → 取"内部所有文件 mtime 的最大值"（＝最近一次实际产出）。
  · **快照总目录（如 `_备份/`）→ 逐个快照单独判龄**，不按整体判。
    因为"取内部最大值"意味着**往里丢一个新快照，整个容器就变年轻**，
    会把内部早已超期的快照全部藏住（曾实测：容器报 1 天，内部 17/34 项已 7–19 天）。
    这类目录由 `is_snapshot_catalog()` 自动识别（名称以 `_备份` 开头，或含 ≥2 个带
    「公众号文章」层级的子目录），报告里会**逐快照展开成一行**。

用法：
  # 只读扫描，输出报告（默认）
  python 工具脚本/过程文件过期扫描_scan_stale.py

  # 指定保留天数（覆盖默认策略）
  python 工具脚本/过程文件过期扫描_scan_stale.py --keep-days A=7,B=7,C=14

  # 输出 markdown 报告到文件
  python 工具脚本/过程文件过期扫描_scan_stale.py --out _档案/报告/00_过程文件扫描_20260911.md

  # 列出某类的完整路径（供人工圈选后另行删除）
  python 工具脚本/过程文件过期扫描_scan_stale.py --list A

  # ⭐ 列出「可自动清理的视频类产物」（过程片段 + 旧版本）—— 供每周任务直接消费
  python 工具脚本/过程文件过期扫描_scan_stale.py --video-garbage

安全：本脚本只读不写（除 --out 指定的报告），不调用任何删除操作。
      **删除一律交给 `工具脚本/trash_to_recycle.py`（送回收站 + 全盘核实）**，本脚本只负责"列出清单"。

⭐ 2026-09-28 新增「视频类产物」维度（用户要求"定期清理视频的过程文件、旧版本文件"）：
  视频**单个体积在 100~700MB**，是全工作区体量的头号来源（实测 50 个 ≈9.5GB）。
  它们和"文档类过程文件"的价值完全不同——**没有任何"可复用提示词"，且 100% 可重出**：
    · `_过程文件/` 里的视频（`_stage0_join.mp4`／`_stage1_cut.mp4` 等）= 管道的中间拼接产物，重跑即重建；
    · `_旧版本/` 里的视频 = 改前备份的成片，由 `md + _素材/` 随时重出。
  → 所以单列出来、**保留期更短（默认 3 天）**，并由每周任务**自动送回收站**（见 `--video-garbage`）。
  ⛔ **绝不列入**：`_素材/`（**拍摄母带，删了不可再生**）、`_成品/成片_*.mp4`（**发布成品**）、
     以及任何非视频文件（ass／png／md／zip）。
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
    "B": (7,    "一次性快照（修复前备份，验证通过后即失效）",
           ["_backup*/", "_备份/"]),
    "C": (14,   "素材类（含可复用提示词与参数）",
           ["_封面候选*/", "_过程文件/", "_未采用*/", "_原始*/", "_归档*/"]),
    "D": (None, "长期归档（报告、长期资产，不自动过期）",
           ["_档案/", "_资产/"]),
    # ⭐ 2026-09-28 新增：视频/成片的**旧版本备份目录**
    #   （与目录里**视频文件**的保留期一致＝3 天；文件级清单见 `collect_video_garbage`）
    "E": (3,    "视频与成片的旧版本备份（可由 md + _素材 重出）",
           ["_旧版本/"]),
}

# 目录名前缀 -> 类别
PREFIX_CAT = {
    "_预览": "A",
    "_backup": "B", "_备份": "B",
    "_封面候选": "C", "_过程文件": "C", "_未采用": "C", "_原始": "C", "_归档": "C",
    "_档案": "D", "_资产": "D",
    "_旧版本": "E",
}

SKIP_DIRS = {".git", ".workbuddy", "__pycache__", "node_modules"}

# ---- 视频类产物（文件级；2026-09-28 立）----
# ⭐ 只在这两个目录里收：一个是管道中间产物，一个是改前备份——**都 100% 可重出**。
# ⛔ 绝不收：`_素材/`（拍摄母带，不可再生）、`_成品/` 根下的 `成片_*.mp4`（发布成品）。
VIDEO_GARBAGE_DIRS = ("_过程文件", "_旧版本")
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".mts", ".avi", ".mkv", ".flv", ".wmv"}
# 保留 3 天的依据（2026-09-28 定）：
#   · `_stage*.mp4` 是**管道内部中间态**——出片完成即无用，重跑约 10 分钟就回来；
#   · `_旧版本/` 的成片是**改版备份**——改版周期通常 1~2 天，3 天已覆盖回退窗口；
#   · 兜底是**回收站**（不自动清空）→ 真需要更早的版本仍能从回收站还原；
#   · 实测这批文件 28 个 / 6.3GB，多留一周就多占一周空间。
VIDEO_KEEP_DAYS = 3


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
    """返回 (size, cnt, newest, oldest)。

    ⛔ **判龄只看"文件真实最后修改时间"（st_mtime），目录自身的时间一概不看。**
    目录 mtime 会在其子项增删时被改写，既不能代表内容新旧，也会随无关操作漂移。
    空目录（无任何文件）返回 newest=0 / oldest=0，由调用方按"未知"处理。
    """
    size = 0
    cnt = 0
    newest = 0.0
    oldest = 0.0
    for r, _, files in os.walk(root):
        for f in files:
            p = os.path.join(r, f)
            try:
                st = os.stat(p)
            except OSError:
                continue
            size += st.st_size
            cnt += 1
            if st.st_mtime > newest:
                newest = st.st_mtime
            if oldest == 0.0 or st.st_mtime < oldest:
                oldest = st.st_mtime
    return size, cnt, newest, oldest


def stat_file(path):
    """单个文件按自身 mtime 判龄，返回 (size, 1, newest, oldest)。"""
    try:
        st = os.stat(path)
    except OSError:
        return 0, 0, 0.0, 0.0
    return st.st_size, 1, st.st_mtime, st.st_mtime


def stat_any(path):
    """文件或目录统一入口：目录走 stat_dir（只看内部文件 mtime），文件走 stat_file。"""
    return stat_dir(path) if os.path.isdir(path) else stat_file(path)


def has_series_level(path, max_depth=4):
    """目录内是否含「公众号文章」层级 —— 整系列快照的特征。用于识别快照容器。"""
    base_len = len(path)
    for r, dirs, _ in os.walk(path):
        if r[base_len:].count(os.sep) >= max_depth:
            dirs[:] = []
            continue
        if any("公众号文章" in d for d in dirs):
            return True
    return False


def is_snapshot_catalog(d, name):
    """判断某过程目录是否为「快照总目录」—— 其子项各自是一次独立快照。

    ⚠️ 快照总目录**不能按整体判龄**：一个目录只取"内部最新文件"，
    等于"往里丢一个新快照，整个容器就变年轻"，会把内部早已超期的快照全部藏住。
    → 命中则改为**逐个快照单独判龄**。
    """
    if name in ("_备份", "_backup", "_backups"):
        return True
    try:
        kids = [os.path.join(d, k) for k in os.listdir(d)]
    except OSError:
        return False
    hits = 0
    for k in kids:
        if os.path.isdir(k) and has_series_level(k):
            hits += 1
            if hits >= 2:
                return True
    return False


def collect_video_garbage(base, keep_days=VIDEO_KEEP_DAYS):
    """文件级收集「可自动清理的视频类产物」（2026-09-28 立）。

    ⭐ 两条判据（**只有这两条**）：
      ① 路径里带 `_过程文件` 目录 —— 管道的中间拼接产物（`_stage0_join.mp4`／`_stage1_cut.mp4`），
         纯中间态，**重跑管道即重建**；
      ② 路径里带 `_旧版本` 目录 —— 改前备份的成片，**由 md ＋ `_素材/` 随时重出**。
    ⛔ 不收：`_素材/`（**拍摄母带，删了不可再生**）、`_成品/` 根下的 `成片_*.mp4`（**发布成品**）、
       以及任何非视频文件（ass／png／md／zip）。

    返回 [{path, size, age, expired, kind}]，按体积降序。
    """
    now = datetime.datetime.now()
    out = []
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        parts = os.path.relpath(root, base).split(os.sep)
        hit = [p for p in VIDEO_GARBAGE_DIRS if p in parts]
        if not hit:
            continue
        kind = "过程片段" if hit[0] == "_过程文件" else "旧版本"
        for f in files:
            if os.path.splitext(f)[1].lower() not in VIDEO_EXT:
                continue
            p = os.path.join(root, f)
            try:
                st = os.stat(p)
            except OSError:
                continue
            age = (now - datetime.datetime.fromtimestamp(st.st_mtime)).days
            out.append({
                "path": os.path.relpath(p, base),
                "size": st.st_size,
                "age": age,
                "expired": age >= keep_days,
                "kind": kind,
            })
    out.sort(key=lambda x: -x["size"])
    return out


def _mb(n):
    return f"{n/1024/1024:.1f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=".", help="工作区根目录（默认当前目录）")
    ap.add_argument("--keep-days", default="", help="覆盖保留天数，如 A=7,B=7,C=14")
    ap.add_argument("--out", default="", help="输出 markdown 报告到该路径")
    ap.add_argument("--list", default="", help="列出指定类别(A/B/C/D/E)的完整路径")
    ap.add_argument("--quiet", action="store_true", help="只输出汇总")
    ap.add_argument("--brief", action="store_true",
                    help="简报模式：只列具体文件夹名 + 建议动作（供定期扫描用）")
    ap.add_argument("--video-garbage", action="store_true",
                    help="只列出「可自动清理的视频类产物」（过程片段 + 旧版本），供定期任务直接消费")
    ap.add_argument("--video-keep-days", type=int, default=VIDEO_KEEP_DAYS,
                    help=f"视频类产物的保留天数（默认 {VIDEO_KEEP_DAYS} 天）")
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

    # ⭐ --video-garbage：只输出「可自动清理的视频类产物」清单
    #    （每周任务直接消费；删除交给 trash_to_recycle.py，本脚本只列清单）
    if args.video_garbage:
        vg = collect_video_garbage(base, args.video_keep_days)
        exp = [v for v in vg if v["expired"]]
        print(f"【视频类产物 · 可自动清理】保留期 {args.video_keep_days} 天")
        print(f"合计 {len(vg)} 个 / {_mb(sum(v['size'] for v in vg))} MB；"
              f"其中超期 {len(exp)} 个 / {_mb(sum(v['size'] for v in exp))} MB")
        print()
        if exp:
            print("-" * 72)
            print("待清清单（超期项，按体积降序；**路径在第一列**，供 trash_to_recycle.py 直接消费）")
            print("-" * 72)
            for v in exp:
                print(f"{v['path']}\t{_mb(v['size'])}M\t{v['age']}天\t{v['kind']}")
            rest = [v for v in vg if not v["expired"]]
            if rest:
                print()
                print(f"（另有未超期 {len(rest)} 个 / {_mb(sum(v['size'] for v in rest))} MB，本次不动）")
        else:
            print("（本周没有超期的视频类产物，无需清理）")
            print()
            print("未超期（仍在保留期内，本次不动）：")
            for v in vg:
                print(f"{v['path']}\t{_mb(v['size'])}M\t{v['age']}天\t{v['kind']}")
        print()
        print("⛔ 本清单不含：`_素材/`（拍摄母带，删了不可再生）、`_成品/成片_*.mp4`（发布成品）、"
              "任何非视频文件（ass／png／md）。")
        return

    def age_of(mtime):
        return (now - datetime.datetime.fromtimestamp(mtime)).days if mtime else -1

    rows = []
    for d, cat in collect(base):
        size, cnt, newest, oldest = stat_dir(d)
        age = age_of(newest)
        keep = policy[cat][0]
        expired = (keep is not None and age >= keep)
        items = []
        # 快照总目录：不能整体判龄，改为逐个快照单独判龄（否则超期快照会被"平均年轻"掉）
        if is_snapshot_catalog(d, os.path.basename(d)):
            try:
                for k in sorted(os.listdir(d)):
                    kp = os.path.join(d, k)
                    ks, kc, kn, ko = stat_any(kp)
                    if kc == 0:
                        continue
                    items.append({
                        "path": k, "size": ks, "cnt": kc,
                        "age": age_of(kn), "keep": keep, "expired": keep is not None and age_of(kn) >= keep,
                    })
            except OSError:
                pass
            items.sort(key=lambda x: -x["size"])
        rows.append({
            "path": os.path.relpath(d, base),
            "cat": cat,
            "size": size,
            "cnt": cnt,
            "age": age,
            "oldest": age_of(oldest),
            "keep": keep,
            "expired": expired,
            "items": items,
        })

    # 快照总目录展开成"每快照一行"的展示行
    def display_rows():
        out = []
        for r in rows:
            if r["items"]:
                for it in r["items"]:
                    out.append({**r, "path": os.path.join(r["path"], it["path"]),
                                "size": it["size"], "cnt": it["cnt"],
                                "age": it["age"], "keep": it["keep"], "expired": it["expired"]})
            else:
                out.append(r)
        return out

    drows = display_rows()

    # --brief 模式：只列具体文件夹名 + 建议动作
    if args.brief:
        total = sum(r["size"] for r in rows)
        exp = [r for r in drows if r["expired"]]
        extra = len(drows) - len(rows)
        cnt_txt = f"（含快照子项展开，共 {len(drows)} 项）" if extra > 0 else ""
        print(f"过程类目录共 {len(rows)} 个 / {total/1024/1024:.1f} MB{cnt_txt}；"
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
            late = [r for r in drows if r["cat"] == cat and r["expired"]]
            expanded = sum(len(r["items"]) for r in sub)
            exp_txt = ""
            if late:
                exp_txt = f"，其中超期 {len(late)} 个"
                if expanded:
                    exp_txt += f"（按快照子项计，本类共 {expanded} 个子项）"
            print(f"  {cat} 类（{'、'.join(pats)}，保留{kd_txt}）：{len(sub)} 个 / "
                  f"{sum(r['size'] for r in sub)/1024/1024:.1f}M" + exp_txt)

        # ⭐ 视频类产物（2026-09-28 新增）：全工作区体量的**头号来源**，且**可自动清理**
        #    （它和文档类过程文件价值不同：没有提示词可摘，且 100% 可重出）
        vg = collect_video_garbage(base, args.video_keep_days)
        if vg:
            ve = [v for v in vg if v["expired"]]
            print()
            print(f"【视频类产物 · 可自动清理（保留 {args.video_keep_days} 天）】")
            print(f"  共 {len(vg)} 个 / {_mb(sum(v['size'] for v in vg))} MB；"
                  f"超期 {len(ve)} 个 / {_mb(sum(v['size'] for v in ve))} MB"
                  + ("　← 本周可自动送回收站" if ve else "　← 本周无超期，不动"))
            for v in ve:
                print(f"  - {v['path']}　{_mb(v['size'])}M · {v['age']}天 · {v['kind']}")
            rest = [v for v in vg if not v["expired"]]
            if rest:
                print(f"  （另有未超期 {len(rest)} 个 / {_mb(sum(v['size'] for v in rest))} MB，本次不动）")
            print("  ⛔ 不含 `_素材/`（拍摄母带）与 `_成品/成片_*.mp4`（发布成品）")
        return

    # --list 模式
    if args.list:
        cat = args.list.strip().upper()
        hit = [r for r in drows if r["cat"] == cat]
        for r in sorted(hit, key=lambda x: -x["size"]):
            print(os.path.join(base, r["path"]))
        print(f"\n共 {len(hit)} 个（{sum(r['size'] for r in hit)/1024/1024:.1f} MB）", file=sys.stderr)
        return

    # 汇总
    total_size = sum(r["size"] for r in rows)
    exp = [r for r in drows if r["expired"]]
    exp_size = sum(r["size"] for r in exp)

    lines = []
    lines.append("# 工作区过程文件扫描报告（只读）")
    lines.append("")
    lines.append(f"> 扫描时间：{now.strftime('%Y-%m-%d %H:%M')}　根目录：`{base}`")
    lines.append("> **本报告只读生成，未删除或移动任何文件。**")
    lines.append("> **判龄口径：一律取「文件真实最后修改时间」；目录自身时间不参与判定。**")
    lines.append("")

    # ---- 最前面：直接给出「该清哪些文件夹」 ----
    lines.append("## 结论（先看这里）")
    lines.append("")
    lines.append(f"过程类目录共 **{len(rows)}** 个、合计 **{total_size/1024/1024:.1f} MB**；"
                 f"其中**已超期 {len(exp)} 个（{exp_size/1024/1024:.1f} MB）**。")
    if any(r["items"] for r in rows):
        lines.append("")
        lines.append("> ⚠️ **快照总目录已展开**：`_备份/` 这类目录的子项各自是一次独立快照，"
                     "已按**每个快照自己的文件时间**单独判龄（不再按整体判，否则新快照会掩盖旧快照的超期）。")
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
        if any(r["items"] for r in sub):
            lines.append("> **⭐ 本类含「快照总目录」，已逐快照展开判龄**（每个子项独立计龄）。")
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
            # 快照总目录：展开子项明细
            for it in r["items"]:
                if it["keep"] is None:
                    iflag = "长期"
                elif it["expired"]:
                    iflag = f"**超期** ({it['age']}天)"
                else:
                    iflag = f"保留 ({it['age']}/{it['keep']}天)"
                lines.append(
                    f"| └ {iflag} | {it['size']/1024/1024:.2f}M | {it['cnt']} | {it['age']}天前 "
                    f"| `{r['path']}/{it['path']}` |"
                )
        lines.append("")

    # ---- 视频类产物（文件级；2026-09-28 新增）----
    vg = collect_video_garbage(base, args.video_keep_days)
    if vg:
        ve = [v for v in vg if v["expired"]]
        lines.append(f"## 视频类产物 · 可自动清理（保留 {args.video_keep_days} 天）"
                     f"　（{len(vg)} 个 / {_mb(sum(v['size'] for v in vg))} MB）")
        lines.append("")
        lines.append(f"其中**超期 {len(ve)} 个 / {_mb(sum(v['size'] for v in ve))} MB**"
                     f"（超期项由每周任务自动送回收站）。")
        lines.append("")
        lines.append("> ⭐ 这两类**都可重出**、**没有提示词要摘录**：")
        lines.append("> · `_过程文件/` 里的视频 ＝ 管道的中间拼接产物（`_stage0_join`／`_stage1_cut`），**重跑即重建**；")
        lines.append("> · `_旧版本/` 里的视频 ＝ 改前备份的成片，**由 md ＋ `_素材/` 随时重出**。")
        lines.append("> ⛔ 本节**不含** `_素材/`（**拍摄母带，删了不可再生**）与 `_成品/成片_*.mp4`（**发布成品**）。")
        lines.append("")
        lines.append("| 状态 | 体积 | 放置 | 类型 | 路径 |")
        lines.append("|---|---|---|---|---|")
        for v in vg:
            flag = (f"**超期** ({v['age']}天)" if v["expired"]
                    else f"保留 ({v['age']}/{args.video_keep_days}天)")
            lines.append(f"| {flag} | {_mb(v['size'])}M | {v['age']}天前 | {v['kind']} | `{v['path']}` |")
        lines.append("")

    lines.append("## 下一步")
    lines.append("")
    lines.append("1. 圈选上表中确认可清的项（A 类通常可全清，B 类确认对应修复已验证通过后可清）")
    lines.append("2. 按 SOP 三步安全清理法执行：`send2trash` 回收站 + 分批 ≤10 项 + 逐批核对")
    lines.append("3. 清理前先 `git commit` 一次，让删除可回滚")
    lines.append("4. 清理后重跑 `系列发布全套自检_selfcheck.py` 确认正式成果零影响")
    lines.append("5. ⭐ **视频类产物**（`_过程文件/` 里的视频 ＋ `_旧版本/` 里的视频）："
                 "跑 `--video-garbage` 取清单，**超期即可直接送回收站**"
                 "（无提示词要摘录、且 100% 可重出，由每周任务自动执行）——"
                 "⛔ 但**绝不碰** `_素材/`（母带）与 `_成品/成片_*.mp4`（发布成品）")
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
