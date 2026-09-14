#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""memory 体积巡检 —— 检查记忆文件是否超过注入限额，并在超限时给出可操作建议。

背景
----
WorkBuddy 会把 `.workbuddy/memory/MEMORY.md` 注入会话上下文，但**有字符上限**：
    工作区 MEMORY.md  限额 3000 字符
    用户级 MEMORY.md  限额 4000 字符
超限会被**静默截断**——Agent 看到的记忆是残缺的，后面的约定实际不生效。
2026-09-14 实测：工作区版曾达 7776 字符（超 2.6 倍），长期被截断而无人察觉。

用法
----
    # 人类可读报告（手动巡检用）
    python 工具脚本/memory体积巡检_check_memory.py

    # 供 SessionStart hook 调用：只在「需要行动」时输出（超限 / 日志超期）
    python 工具脚本/memory体积巡检_check_memory.py --hook

    # JSON 输出（脚本化调用）
    python 工具脚本/memory体积巡检_check_memory.py --json

退出码
------
    0  一切正常（或仅提示）
    0  超限时**仍返回 0**——因为 SessionStart hook 的非零退出码会被当作执行失败，
       本脚本改用 stdout 传递提醒。
"""
import argparse
import datetime
import json
import os
import sys

# ---- 限额（与 WorkBuddy 注入规则一致）----
WORKSPACE_LIMIT = 3000
USER_LIMIT = 4000
LOG_ARCHIVE_DAYS = 30  # 日志超此天数建议蒸馏进 MEMORY.md 后归档

# ---- 路径 ----
WORKSPACE_ROOT = r"D:\个人资料\家庭教育"
USER_MEMORY = os.path.join(os.path.expanduser("~"), ".workbuddy", "MEMORY.md")


def char_count(path):
    """返回字符数；文件不存在返回 None。"""
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return len(f.read())
    except Exception:
        return None


def check_memories():
    """检查两份 MEMORY.md，返回 [(名称, 路径, 字符数, 限额, 是否超限)]。"""
    targets = [
        ("工作区 MEMORY.md", os.path.join(WORKSPACE_ROOT, ".workbuddy", "memory", "MEMORY.md"), WORKSPACE_LIMIT),
        ("用户级 MEMORY.md", USER_MEMORY, USER_LIMIT),
    ]
    out = []
    for name, path, limit in targets:
        n = char_count(path)
        if n is None:
            continue
        out.append((name, path, n, limit, n > limit))
    return out


def check_logs():
    """检查 memory 目录下的日志文件是否有超期未归档的。返回 (总数, 超期列表)。"""
    d = os.path.join(WORKSPACE_ROOT, ".workbuddy", "memory")
    if not os.path.isdir(d):
        return 0, []
    today = datetime.date.today()
    stale = []
    total = 0
    for f in sorted(os.listdir(d)):
        if not f.endswith(".md") or f == "MEMORY.md":
            continue
        try:
            dt = datetime.datetime.strptime(f[:-3], "%Y-%m-%d").date()
        except ValueError:
            continue
        total += 1
        age = (today - dt).days
        if age > LOG_ARCHIVE_DAYS:
            stale.append((f, age))
    return total, stale


def human_report(memories, log_total, stale_logs):
    lines = ["=== memory 体积巡检 ===", ""]
    over = []
    for name, path, n, limit, is_over in memories:
        flag = "❌ 超限" if is_over else "✅"
        pct = n / limit * 100
        lines.append(f"  {flag} {name}: {n} / {limit} 字符（{pct:.0f}%）")
        if is_over:
            over.append((name, n - limit))
    lines.append("")
    lines.append(f"  日志文件: {log_total} 个，超 {LOG_ARCHIVE_DAYS} 天未归档 {len(stale_logs)} 个")
    if stale_logs:
        for f, age in stale_logs:
            lines.append(f"      ⚠️ {f}（{age} 天）→ 应蒸馏进 MEMORY.md 后归档")
    lines.append("")
    if over:
        lines.append("  【建议】超限记忆请精简：**细则移交专家包 SOP，只留项目约定与红线**。")
        for name, excess in over:
            lines.append(f"      {name} 需再减 {excess} 字符")
    else:
        lines.append("  ✅ 全部达标，无需处理")
    return "\n".join(lines)


def hook_output(memories, stale_logs):
    """SessionStart hook 输出：只在需要行动时输出；正常则完全静默。"""
    msgs = []
    for name, path, n, limit, is_over in memories:
        if is_over:
            msgs.append(
                f"[memory 体积巡检] ⚠️ {name} 已达 {n} 字符，超过注入限额 {limit} "
                f"（超 {n - limit}）——**当前会话注入会被静默截断，记忆不完整**。"
                f"请先精简：细则移交专家包 SOP，只留项目约定与红线。路径：{path}"
            )
    for f, age in stale_logs:
        msgs.append(
            f"[memory 体积巡检] 日志 {f} 已 {age} 天未归档，"
            f"建议蒸馏进 MEMORY.md 后删除（规则：超 30 天归档）。"
        )
    return "\n".join(msgs)


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--hook", action="store_true", help="SessionStart hook 模式：仅在需行动时输出")
    ap.add_argument("--json", action="store_true", help="JSON 输出")
    args = ap.parse_args()

    memories = check_memories()
    log_total, stale_logs = check_logs()

    if args.json:
        print(json.dumps({
            "memories": [
                {"name": n, "path": p, "chars": c, "limit": lim, "over": o}
                for n, p, c, lim, o in memories
            ],
            "logs": {"total": log_total, "stale": [{"file": f, "days": a} for f, a in stale_logs]},
        }, ensure_ascii=False, indent=2))
        return 0

    if args.hook:
        out = hook_output(memories, stale_logs)
        if out:
            print(out)
        return 0

    print(human_report(memories, log_total, stale_logs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
