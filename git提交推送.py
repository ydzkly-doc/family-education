#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""一键提交并推送（add → commit → push）

用途：把当前工作区的改动一次性提交并推送到远程。
      放在仓库根目录，双击或命令行运行即可。

用法：
  python git提交推送.py                    # 交互式：自动生成提交信息，可修改确认
  python git提交推送.py -m "提交说明"       # 直接指定提交信息
  python git提交推送.py -y                 # 跳过所有确认（谨慎使用）
  python git提交推送.py --dry-run          # 只看会提交什么，不做任何改动
  python git提交推送.py --push-only        # 跳过 add/commit，只推送已有提交
  python git提交推送.py --no-verify-save   # 跳过"过程文件入库"检查（不推荐）

安全设计（针对本仓库的已知坑）：
  1. 提交前扫描待提交清单，若含【过程目录 / 缓存 / 大文件】会明确警告并可中止。
     本仓库大量使用 _预览/ _过程文件/ _封面候选/ 等过程目录，误入库过一次 60MB。
  2. 推送后用 `git ls-remote` 与本地 HEAD 比对来判定成败
     —— 不能只看 `git status`：本仓库存在并发进程清理 refs/remotes 的情况，
     会让 status 显示 [gone] 造成"推送失败"的假象。
  3. 大仓库（本仓库 .git 约 420MB）推送耗时超过 1 分钟属正常，脚本会等待完成。
"""
import argparse
import os
import subprocess
import sys

# ---------------- 配置 ----------------

GIT_EXE = "git"          # 若 git 不在 PATH，改成绝对路径，如 r"C:\Program Files\Git\bin\git.exe"

# 过程目录/缓存：绝不应进入版本库
FORBIDDEN_PARTS = [
    "_预览", "_过程文件", "_封面候选", "_封面", "_未采用", "_原始", "_原始png",
    "_归档", "_备份", "_backup", "__pycache__", ".tmp", ".pyc", ".DS_Store",
    "node_modules",
]

# 超过该体积的文件会提示确认（字节）
BIG_FILE_BYTES = 5 * 1024 * 1024

# 提交信息模板：按实际改动自动填充
DEFAULT_MSG = "内容更新"

# ---------------- 基础工具 ----------------


def run(args, check=False, capture=True):
    """执行 git 命令。返回 CompletedProcess。"""
    full = [GIT_EXE] + args
    r = subprocess.run(
        full, capture_output=capture, text=True,
        encoding="utf-8", errors="replace",
    )
    if check and r.returncode != 0:
        print("\n❌ git 命令失败：git " + " ".join(args))
        if r.stdout:
            print(r.stdout.strip())
        if r.stderr:
            print(r.stderr.strip())
        sys.exit(1)
    return r


def out(args):
    """执行并返回 stdout（去首尾空白）。"""
    return (run(args).stdout or "").strip()


def hr(title=""):
    print("\n" + "=" * 62)
    if title:
        print(title)
        print("=" * 62)


def ask(prompt, default_yes=True):
    """是/否确认。非交互环境直接返回默认值。"""
    if not sys.stdin.isatty():
        return default_yes
    tip = "[Y/n]" if default_yes else "[y/N]"
    try:
        a = input(f"{prompt} {tip} ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    if not a:
        return default_yes
    return a in ("y", "yes", "是")


# ---------------- 步骤 ----------------


def preflight():
    """前置检查：必须在 git 仓库内、必须有远程。"""
    hr("一、环境检查")

    r = run(["rev-parse", "--is-inside-work-tree"])
    if r.returncode != 0:
        print("❌ 当前目录不是 git 仓库。请把本脚本放在仓库根目录运行。")
        sys.exit(1)

    # 仓库根目录（脚本可能被放到子目录运行）
    top = out(["rev-parse", "--show-toplevel"])
    if top and os.path.abspath(top) != os.path.abspath(os.getcwd()):
        print(f"⚠️  当前目录不是仓库根目录，实际根目录：{top}")
        print(f"   脚本将切换到：{top}")
        os.chdir(top)

    branch = out(["rev-parse", "--abbrev-ref", "HEAD"])
    remotes = [l for l in out(["remote"]).splitlines() if l.strip()]
    remote = remotes[0] if remotes else ""

    print(f"  分支      : {branch}")
    print(f"  远程      : {remote or '(无)'}")
    if not remote:
        print("\n❌ 没有配置远程仓库，无法推送。")
        sys.exit(1)

    return branch, remote


def show_changes():
    """列出待提交内容，返回 (files, forbidden, bigs)。"""
    hr("二、待提交内容")

    r = run(["status", "--porcelain"])
    lines = [l for l in (r.stdout or "").splitlines() if l.strip()]
    if not lines:
        return [], [], []

    stats = {}
    files = []
    for l in lines:
        code = l[:2].strip() or "??"
        path = l[3:].strip().strip('"')
        files.append((code, path))
        stats[code] = stats.get(code, 0) + 1

    print(f"  共 {len(files)} 项改动：")
    for code in sorted(stats):
        print(f"    {code:<4} {stats[code]:>4} 项")

    forbidden, bigs = [], []
    for code, path in files:
        norm = path.replace("\\", "/")
        if any(part in norm for part in FORBIDDEN_PARTS):
            forbidden.append(path)
        full = os.path.join(os.getcwd(), path)
        if os.path.isfile(full):
            try:
                if os.path.getsize(full) > BIG_FILE_BYTES:
                    bigs.append((os.path.getsize(full), path))
            except OSError:
                pass

    return files, forbidden, bigs


def verify_no_junk(forbidden, bigs, skip=False):
    """过程文件 / 大文件检查。有问题时允许中止。"""
    if skip:
        print("\n  ⏭️  已跳过过程文件检查（--no-verify-save）")
        return

    if not forbidden and not bigs:
        print("\n  ✅ 过程文件检查通过（无过程目录、无超大文件）")
        return

    hr("⚠️  安全检查发现问题")

    if forbidden:
        print(f"  【过程目录/缓存】共 {len(forbidden)} 项，本不应进入版本库：")
        for p in forbidden[:15]:
            print(f"    - {p}")
        if len(forbidden) > 15:
            print(f"    ...另 {len(forbidden) - 15} 项")
        print("\n    建议：先检查 .gitignore 是否覆盖这些路径；")
        print("          若是已被跟踪的旧文件，需 `git rm -r --cached <路径>` 才会生效。")

    if bigs:
        print(f"\n  【大文件 > {BIG_FILE_BYTES // 1024 // 1024}MB】共 {len(bigs)} 个：")
        for size, p in sorted(bigs, reverse=True)[:10]:
            print(f"    {size / 1024 / 1024:>8.2f} MB  {p}")

    print("\n  ⛔ 脚本不会自动清理。请先处理，或明确选择继续。")
    if not ask("  仍要继续提交吗？", default_yes=False):
        print("\n  已中止，未做任何改动。")
        sys.exit(0)


def do_add():
    hr("三、暂存（git add -A）")
    r = run(["add", "-A"])
    if r.returncode != 0:
        print("❌ git add 失败：")
        print((r.stderr or r.stdout or "").strip())
        sys.exit(1)
    n = len([l for l in out(["diff", "--cached", "--name-only"]).splitlines() if l.strip()])
    print(f"  ✅ 已暂存 {n} 个文件")
    return n


def do_commit(msg):
    hr("四、提交（git commit）")
    print("  提交信息：")
    for line in msg.splitlines():
        print(f"    {line}")

    # 用临时文件传信息，避免中文/多行在管道中的编码问题
    tmp = os.path.join(os.getcwd(), ".git", "COMMIT_MSG_TMP.txt")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(msg if msg.endswith("\n") else msg + "\n")
        r = run(["commit", "-F", tmp])
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass

    if r.returncode != 0:
        blob = ((r.stdout or "") + (r.stderr or "")).strip()
        if "nothing to commit" in blob or "无文件要提交" in blob:
            print("  ℹ️  没有需要提交的改动。")
            return False
        print("❌ 提交失败：")
        print(blob)
        sys.exit(1)

    sha = out(["rev-parse", "--short", "HEAD"])
    print(f"\n  ✅ 已提交：{sha}")
    return True


def do_push(branch, remote):
    hr("五、推送（git push）")
    print(f"  推送到 {remote}/{branch} ...")
    print("  提示：本仓库 .git 较大，推送 1–2 分钟属正常，请勿中断。\n")

    r = run(["push", remote, branch])
    blob = ((r.stdout or "") + (r.stderr or "")).strip()

    if r.returncode != 0:
        print("❌ git push 返回非零：")
        print(blob or "(无输出)")
        print("\n  常见原因：网络问题、需要登录、远程有新提交需先 pull。")
        print("  可重试：python git提交推送.py --push-only")
        sys.exit(1)

    if blob:
        print("  " + blob.replace("\n", "\n  "))


def verify_push(branch, remote):
    """权威判定：用 ls-remote 比对远程与本地 HEAD。

    ⚠️ 不用 `git status`：本仓库存在并发进程清理 refs/remotes，
       会让 status 误显示 [gone]，看起来像推送失败，实际已成功。
    """
    hr("六、验证推送结果")

    local = out(["rev-parse", "HEAD"])
    r = run(["ls-remote", remote, f"refs/heads/{branch}"])
    remote_sha = ""
    for line in (r.stdout or "").splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1].endswith(f"/{branch}"):
            remote_sha = parts[0]
            break

    print(f"  本地 HEAD          : {local[:12]}")
    print(f"  远程 {remote}/{branch:<8} : {(remote_sha[:12] if remote_sha else '(读取失败)')}")

    if remote_sha and remote_sha == local:
        print("\n  ✅ 推送成功——远程与本地完全一致。")
        return True

    print("\n  ❌ 远程与本地不一致，推送可能未生效。")
    print("     可重试：python git提交推送.py --push-only")
    return False


def confirm_message(files):
    """生成/确认提交信息。"""
    hr("三、提交信息")

    n_add = sum(1 for c, _ in files if c == "??" or c == "A")
    n_mod = sum(1 for c, _ in files if c == "M")
    n_del = sum(1 for c, _ in files if c == "D")
    n_ren = sum(1 for c, _ in files if c == "R")

    parts = []
    if n_mod:
        parts.append(f"修改 {n_mod}")
    if n_add:
        parts.append(f"新增 {n_add}")
    if n_ren:
        parts.append(f"重命名 {n_ren}")
    if n_del:
        parts.append(f"删除 {n_del}")

    default = f"{DEFAULT_MSG}：{' / '.join(parts)}" if parts else DEFAULT_MSG

    print(f"  建议信息：{default}")
    print("\n  （直接回车用建议信息；也可输入自定义说明）")

    if not sys.stdin.isatty():
        return default

    try:
        a = input("  提交信息 > ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)
    return a or default


# ---------------- 主流程 ----------------


def main():
    ap = argparse.ArgumentParser(description="一键 add → commit → push")
    ap.add_argument("-m", "--message", default="", help="提交信息（不填则交互输入）")
    ap.add_argument("-y", "--yes", action="store_true", help="跳过所有确认")
    ap.add_argument("--dry-run", action="store_true", help="只看会提交什么，不做改动")
    ap.add_argument("--push-only", action="store_true", help="跳过 add/commit，只推送")
    ap.add_argument("--no-verify-save", action="store_true", help="跳过过程文件检查")
    args = ap.parse_args()

    os.chdir(os.path.dirname(os.path.abspath(__file__)) or ".")
    branch, remote = preflight()

    if args.push_only:
        do_push(branch, remote)
        verify_push(branch, remote)
        return

    files, forbidden, bigs = show_changes()

    if not files:
        print("\n  ℹ️  没有待提交的改动。")
        if ask("  仍然尝试推送已有提交吗？", default_yes=False):
            do_push(branch, remote)
            verify_push(branch, remote)
        return

    if args.dry_run:
        print("\n  🔍 dry-run：以上为将提交的内容，未做任何改动。")
        if forbidden:
            print(f"  ⚠️ 其中 {len(forbidden)} 项属过程目录，正式提交前会被拦下确认。")
        return

    verify_no_junk(forbidden, bigs, skip=args.no_verify_save)

    msg = args.message or confirm_message(files)

    if not args.yes:
        if not ask(f"\n  确认执行 add → commit → push ？（{len(files)} 项改动）"):
            print("\n  已取消，未做任何改动。")
            return

    do_add()
    committed = do_commit(msg)

    if not committed:
        print("\n  无新提交，跳过推送。")
        return

    do_push(branch, remote)
    ok = verify_push(branch, remote)

    hr()
    print("  ✅ 全部完成。" if ok else "  ⚠️ 提交已建立，但推送验证未通过，请检查上方输出。")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  已被用户中断。")
        sys.exit(130)
