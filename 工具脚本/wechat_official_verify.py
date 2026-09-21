# -*- coding: utf-8 -*-
"""微信官方文章结构检测 · 一键调用（权威判据）

═══════════════════════════════════════════════════════════════════════════
  这个脚本解决什么
═══════════════════════════════════════════════════════════════════════════

微信官方有一份《公众平台编辑器插件开发规范》，并开源了配套的**真机检测工具**
（puppeteer 驱动真实 Chromium 跑全规则）。它是唯一**权威判据**——
本项目的 `微信HTML规范校验修复_wx_html_fix.py` 只是**启发式前端筛查**，
无法复现官方基于真实布局测量的判定（实测：同一段「单独测 FAIL、放进整篇 PASS」）。

本脚本 = 官方工具的**自动发现 / 自动安装 / 批量调用**封装，
免去每次手工 clone + npm install。

───────────────────────────────────────────────────────────────────────────
  为什么不在仓库里放官方工具本体
───────────────────────────────────────────────────────────────────────────
  官方工具 = 源码 34KB + 编译产物 157KB + **puppeteer 依赖 101MB**。
  把 101MB 依赖塞进 git 仓库不合理。本脚本改为：
    · 首次运行 → 自动 clone 官方仓库 + npm install 到用户缓存目录
    · 之后运行 → 直接复用缓存（缓存位置见下）
    · 缓存丢失 → 自动重装（幂等）

───────────────────────────────────────────────────────────────────────────
  用法
───────────────────────────────────────────────────────────────────────────
  # 检测单篇
  python 工具脚本/微信官方结构检测_wechat_verify.py 正文.html

  # 检测一个系列的全部正文（自动发现）
  python 工具脚本/微信官方结构检测_wechat_verify.py --dir 青春期30讲/公众号文章

  # 全工作区扫描（默认扫全部系列正文）
  python 工具脚本/微信官方结构检测_wechat_verify.py --all

  # 只看某条规则 / 只看有问题的
  python 工具脚本/微信官方结构检测_wechat_verify.py --all --rule line-height
  python 工具脚本/微信官方结构检测_wechat_verify.py --all --only-bad

  # 详情（打印违规节点 HTML + 测量值）
  python 工具脚本/微信官方结构检测_wechat_verify.py 正文.html --detail

  # 环境自检（不检测，只确认工具可用）
  python 工具脚本/微信官方结构检测_wechat_verify.py --setup

───────────────────────────────────────────────────────────────────────────
  ⚠️ 环境要点（踩过的坑）
───────────────────────────────────────────────────────────────────────────
  · npm install 必须在 **PowerShell** 下跑。在 Git Bash 里 npm 会触发
    wsl.exe，被本机安全策略拦截（已实证）。
  · 首次安装约 2–3 分钟（含下载 Chromium）。
  · 官方检测 3 档屏宽：585 / 677 / 375 px（取最严）；viewport 677×800。
  · 官方支持的 17 条规则见 `--list-rules`。
    ⚠️ 其中 `font-family` **有函数但未调用**（文档有、检测器不查）——
       所以「检测通过」≠「符合文档」，生成阶段仍须遵守规范。

───────────────────────────────────────────────────────────────────────────
  只读声明
───────────────────────────────────────────────────────────────────────────
  本脚本只读正文、只写自己的临时文件，**绝不修改被检测的正文**。
"""
import argparse
import glob
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

# ---------------------------------------------------------------- 常量
REPO = "https://github.com/wechatjs/verify-article-structure-spec.git"
CACHE = os.path.join(os.path.expanduser("~"), ".workbuddy", "cache", "wechat-verify-spec")
CLI_SUBDIR = "cli"

# 官方支持的规则键（源码 cli/engine/rules-text.ts 的 propertyRules）
OFFICIAL_RULES = [
    ("font-family", "自定义字体族", "⚠️ 文档有、检测器未实现调用（生成阶段仍须遵守）"),
    ("opacity", "图片 opacity:0 叠加 SVG", ""),
    ("caret-color", "光标色透明", ""),
    ("line-height", "line-height:0", ""),
    ("line-height-overlapping", "行高小于字体大小、多行重叠", ""),
    ("width", "固定宽：居中不一致 / 溢出 / 宽度差异", "含 3 个子类"),
    ("height", "height:0", ""),
    ("height-nodisplay", "内容溢出容器", ""),
    ("text-align", "text-align:start/end", ""),
    ("animate-begin", "SVG 动画仅 touchstart", ""),
    ("pre", "pre 标签", ""),
    ("nestNodes", "DOM 嵌套层级过深（冗余嵌套）", "对应文档 2.1"),
    ("span-leaf", "span[leaf] 内含块级元素", ""),
    ("node-leaf", "section[nodeleaf] 结构不符规范", ""),
    ("redundant-node", "冗余空子节点过多", ""),
    ("darkmode-low-contrast", "文字与背景对比度太低", ""),
    ("darkmode-no-gradient", "文字背景使用了渐变", ""),
]

VAS_SRC_PATTERNS = [
    "*/公众号文章/发布包_*/**/正文_*.html",
    "*/*/公众号文章/发布包_*/**/正文_*.html",
    "*/公众号文章/发布包_*/正文_*.html",
    "*/*/公众号文章/发布包_*/正文_*.html",
]


def workspace_root():
    """本脚本位于 <root>/工具脚本/，故 root = 上一级"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---------------------------------------------------------------- 环境
def find_pwsh():
    for exe in ("pwsh", "powershell"):
        p = shutil.which(exe)
        if p:
            return p
    return None


def run_npm_install(cli_dir):
    """npm install —— 必须用 PowerShell（bash 下 npm 会触发 wsl.exe 被拦）"""
    print("  正在安装官方工具依赖（首次约 2–3 分钟，含 Chromium 下载）...")
    ps = find_pwsh()
    if not ps:
        print("  ✗ 找不到 PowerShell，无法自动安装。")
        print("    请手动执行：cd \"%s\" && npm install" % cli_dir)
        return False
    cmd = ("Set-Location -LiteralPath '%s'; "
           "& npm install --no-audit --no-fund 2>&1 | Out-File -FilePath '%s' -Encoding utf8"
           % (cli_dir, os.path.join(cli_dir, "_npm_install.log")))
    try:
        r = subprocess.run([ps, "-NoProfile", "-NonInteractive", "-Command", cmd],
                           capture_output=True, text=True, timeout=900)
    except Exception as e:
        print("  ✗ 安装异常：%s" % e)
        return False
    ok = os.path.isdir(os.path.join(cli_dir, "node_modules", "puppeteer"))
    if not ok:
        log = os.path.join(cli_dir, "_npm_install.log")
        if os.path.isfile(log):
            tail = io.open(log, encoding="utf-8", errors="replace").read()[-800:]
            print("  安装日志尾部：\n%s" % tail)
    return ok


def ensure_tool(quiet=False):
    """确保官方工具可用；返回 cli 目录（失败返回 None）"""
    cli = os.path.join(CACHE, CLI_SUBDIR)

    if not os.path.isdir(os.path.join(cli, "src")):
        if not quiet:
            print("  未发现官方工具缓存，首次准备中……")
            print("  缓存目录：%s" % CACHE)
        os.makedirs(CACHE, exist_ok=True)
        if not shutil.which("git"):
            print("  ✗ 找不到 git，无法自动获取官方工具。")
            print("    请手动：git clone %s \"%s\"" % (REPO, CACHE))
            return None
        r = subprocess.run(["git", "clone", "--depth", "1", REPO, CACHE],
                           capture_output=True, text=True)
        if r.returncode != 0 and not os.path.isdir(os.path.join(cli, "src")):
            print("  ✗ clone 失败：%s" % (r.stderr or "")[:300])
            return None
        if not quiet:
            print("  ✓ 官方仓库已就绪")

    if not os.path.isdir(os.path.join(cli, "node_modules")):
        if not run_npm_install(cli):
            return None
        if not quiet:
            print("  ✓ 依赖已安装")
    return cli


# ---------------------------------------------------------------- 检测
RUNNER = r"""
// 批量检测器（复用同一浏览器实例）
// 用法: npx tsx _wx_verify_runner.mjs <清单文件> <输出json>
import fs from 'node:fs';
import path from 'node:path';
import { launchBrowser, runVerify } from './src/browser-runner.ts';

const listFile = process.argv[2];
const outFile = process.argv[3];
const files = fs.readFileSync(listFile, 'utf8').split(/\r?\n/).map(s => s.trim()).filter(Boolean);

const { browser, page } = await launchBrowser({});
const out = [];
for (const f of files) {
  let html;
  try { html = fs.readFileSync(f, 'utf8'); }
  catch (e) { out.push({ file: f, error: 'read failed' }); continue; }
  try {
    const r = await runVerify(page, html, 30000);
    const info = r.inValidInfo || {};
    const groups = Object.keys(info).map(k => {
      const g = info[k] || {};
      const items = g.items || g.nodes || [];
      return {
        key: k,
        count: items.length,
        desc: String(g.violateRules || g.message || '').slice(0, 200),
        samples: items.slice(0, 5).map(x => ({
          html: String(x.outerHTML || x.html || '').slice(0, 600),
          paragraphIndex: x.paragraphIndex,
        })),
      };
    }).filter(g => g.count > 0);
    out.push({ file: f, isValid: r.isValid, groups });
  } catch (e) {
    out.push({ file: f, error: String(e).slice(0, 200) });
  }
}
fs.writeFileSync(outFile, JSON.stringify(out, null, 1), 'utf8');
console.log('WROTE ' + outFile);
await browser.close();
"""


def discover(target_dir):
    """发现正文 html。
    target_dir 给定时：既按「目录下的系列模式」找，也直接递归找该目录内所有 正文_*.html。
    """
    files = []
    if target_dir:
        base = os.path.abspath(target_dir)
        # ① 该目录本身就是「公众号文章」层 或 其下有发布包
        files += glob.glob(os.path.join(base, "**", "正文_*.html"), recursive=True)
        # ② 该目录是系列根目录（其下有 公众号文章/）
        for p in VAS_SRC_PATTERNS:
            files += glob.glob(os.path.join(base, p), recursive=True)
    else:
        base = workspace_root()
        for p in VAS_SRC_PATTERNS:
            files += glob.glob(os.path.join(base, p), recursive=True)
    return sorted(set(f for f in files
                      if "_备份" not in f and "_backup" not in f
                      and os.path.isfile(f)))


def run_verify(files, cli, quiet=False):
    runner = os.path.join(cli, "_wx_verify_runner.mjs")
    io.open(runner, "w", encoding="utf-8").write(RUNNER)

    # Windows 下 npx 是 .cmd，直接调 "npx" 会 WinError 2
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    if not npx:
        for cand in (r"C:\Program Files\nodejs\npx.cmd",
                     os.path.join(os.environ.get("APPDATA", ""), "npm", "npx.cmd")):
            if os.path.isfile(cand):
                npx = cand
                break
    if not npx:
        print("  ✗ 找不到 npx（需 Node.js）。请安装 Node 后重试。")
        return None

    with tempfile.TemporaryDirectory() as td:
        lst = os.path.join(td, "list.txt")
        outp = os.path.join(td, "result.json")
        io.open(lst, "w", encoding="utf-8").write("\n".join(files))
        r = subprocess.run([npx, "tsx", "_wx_verify_runner.mjs", lst, outp],
                           cwd=cli, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=3600,
                           shell=False)
        if not os.path.isfile(outp):
            print("  ✗ 检测失败（未产出结果）")
            err = (r.stderr or r.stdout or "")[-900:]
            print("  输出尾部：%s" % err)
            return None
        return json.load(io.open(outp, encoding="utf-8"))


# ---------------------------------------------------------------- 报告
def report(result, args):
    base = workspace_root()
    if args.rule:
        result = [dict(x, groups=[g for g in x.get("groups", []) if g["key"] == args.rule])
                  for x in result]
    if args.only_bad:
        result = [x for x in result if x.get("groups")]

    n_bad = sum(1 for x in result if x.get("groups"))
    n_err = sum(1 for x in result if x.get("error"))

    print()
    print("=" * 80)
    print("  微信官方结构检测 · 共 %d 篇" % len(result))
    print("=" * 80)

    if not args.rule and not args.only_bad:
        import collections
        cnt = collections.Counter()
        tot = collections.Counter()
        for x in result:
            for g in x.get("groups", []):
                cnt[g["key"]] += 1
                tot[g["key"]] += g["count"]
        if cnt:
            print("  %-28s %-10s %s" % ("规则", "篇数", "处数"))
            print("  " + "-" * 56)
            for k, n in cnt.most_common():
                print("  %-28s %-10s %d" % (k, "%d 篇" % n, tot[k]))
        else:
            print("  ✅ 无任何违规")
        print()

    print("  违规 %d 篇 ｜ 执行异常 %d 篇" % (n_bad, n_err))
    print()
    for x in result:
        gs = x.get("groups", [])
        if not gs and not x.get("error"):
            if args.only_bad:
                continue
            continue
        rel = os.path.relpath(x["file"], base)
        if x.get("error"):
            print("  ⚠️ %s" % rel)
            print("      %s" % x["error"])
            continue
        tag = " ".join("%s:%d" % (g["key"], g["count"]) for g in gs)
        print("  ❌ %-30s %s" % (tag, rel))
        if args.detail:
            for g in gs:
                print("     ── %s ──" % g["key"])
                print("        %s" % g.get("desc", "")[:160])
                for s in g.get("samples", [])[:3]:
                    print("        [段%s] %s" % (s.get("paragraphIndex"),
                                                 s["html"].replace("\n", " ")[:280]))


# ---------------------------------------------------------------- CLI
def main():
    ap = argparse.ArgumentParser(
        description="微信官方文章结构检测（真机 puppeteer，权威判据）",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*", help="要检测的 html（可多个）")
    ap.add_argument("--dir", help="检测该目录下所有正文（自动发现）")
    ap.add_argument("--all", action="store_true", help="扫描全工作区正文")
    ap.add_argument("--rule", help="只看某条规则")
    ap.add_argument("--only-bad", action="store_true", help="只列出有问题的")
    ap.add_argument("--detail", action="store_true", help="打印违规节点 HTML")
    ap.add_argument("--setup", action="store_true", help="只做环境准备自检")
    ap.add_argument("--list-rules", action="store_true", help="列出官方支持的规则")
    args = ap.parse_args()

    if args.list_rules:
        print("官方检测器支持的规则（%d 条）：" % len(OFFICIAL_RULES))
        print()
        for k, name, note in OFFICIAL_RULES:
            print("  %-26s %s%s" % (k, name, ("　← " + note) if note else ""))
        print()
        print("  ⚠️ font-family：源码有 checkFontFamilyViolation()，但 collect.ts 未调用。")
        print("     文档明确「不建议设置任何字体族」，生成阶段须自行遵守。")
        return

    cli = ensure_tool()
    if not cli:
        sys.exit(2)

    if args.setup:
        print("  ✅ 官方工具可用：%s" % cli)
        return

    if args.files:
        files = [os.path.abspath(f) for f in args.files]
        miss = [f for f in files if not os.path.isfile(f)]
        if miss:
            print("  ✗ 文件不存在：%s" % miss[:3])
            sys.exit(1)
    elif args.dir:
        files = discover(os.path.abspath(args.dir))
        if not files:
            print("  该目录下未发现正文 html：%s" % args.dir)
            sys.exit(1)
    elif args.all:
        files = discover(None)
    else:
        ap.print_help()
        return

    print("  待检测 %d 篇（首次启动浏览器 + 逐篇真机渲染，约 2–8 分钟）" % len(files))
    result = run_verify(files, cli)
    if result is None:
        sys.exit(1)
    report(result, args)


if __name__ == "__main__":
    main()
