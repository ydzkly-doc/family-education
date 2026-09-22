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
  python 工具脚本/wechat_official_verify.py 正文.html --detail

  # 环境自检 · 官方探针（不检测，只确认 puppeteer + 全规则跑通）
  python 工具脚本/wechat_official_verify.py --setup

───────────────────────────────────────────────────────────────────────────
  姊妹命令 dedupe —— 冗余嵌套清理（治 nestNodes）
───────────────────────────────────────────────────────────────────────────
  `check` 报「哪里有冗余嵌套」，官方 `dedupe` 直接**把冗余层真删掉**并输出清理后的
  HTML，形成「检测 → 清理 → 复测」闭环。实测（你是孩子最好的玩具·第1篇）：
      nestNodes 4 处 → 0 处，isValid False → True，可见文本逐字未变。

  # 预览清理效果（只出报告，不改文件）
  python 工具脚本/wechat_official_verify.py --dedupe 正文.html --dry-run

  # 清理并写回（自动备份原件到 _备份/dedupe前_<时间戳>/）
  python 工具脚本/wechat_official_verify.py --dedupe 正文.html

  ⚠️ dedupe 输出的**已知格式归一**（不影响可见内容，但需知晓）：
     · 剥掉 `<html>/<head>/<body>` 外壳 → 只留正文片段
       （本工具会自动**回填外壳**并保留 `<title>`，与原件一致）
     · `<br>` → `<br/>`（自闭合，HTML 等价）
     · 属性引号统一双引号；缩进重排
     · 保真：剔除全部标签后的可见文本**逐字一致**（已实证）

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
  · Windows 下 `npx` 是 `npx.cmd`，直接传 "npx" 会 WinError 2。
  · ⚠️ 官方检测结果**按规则名分组**，不同规则互不相干。
    `line-height`（行高叠字）与 `nestNodes`（嵌套过深）是两条独立规则，
    排查时**务必按规则名分开看**，否则会把一个问题误当另一个没修净。

───────────────────────────────────────────────────────────────────────────
  只读声明
───────────────────────────────────────────────────────────────────────────
  本脚本默认只读正文、只写自己的临时文件。
  唯一会写正文的入口是 `--dedupe`（显式指定），且**写前强制备份**。
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
# ⚠️ 2026-09-22 复核（逐函数统计 collect.ts 调用次数）：
#    · 唯一「函数已实现但 collect.ts 未调用」= checkFontFamilyViolation（调用 0 次）
#    · 其余 8 个 check* 函数均已接入
#    · 另有 7 条规范章节**根本没有对应实现**（见 --list-rules 的说明）
OFFICIAL_RULES = [
    ("font-family", "自定义字体族（文档第 3 章）", "⛔ 函数已实现但未接入 → 检测器不查"),
    ("opacity", "图片 opacity:0 叠加 SVG", ""),
    ("caret-color", "光标色透明", ""),
    ("line-height", "line-height:0", ""),
    ("line-height-overlapping", "行高小于字体大小、多行重叠", "文档 1.3"),
    ("width", "固定宽：居中不一致 / 溢出 / 宽度差异", "含 3 个子类"),
    ("height", "height:0", ""),
    ("height-nodisplay", "内容溢出容器", "文档 1.5.2"),
    ("text-align", "text-align:start/end", ""),
    ("animate-begin", "SVG 动画仅 touchstart", ""),
    ("pre", "pre 标签", ""),
    ("nestNodes", "DOM 嵌套层级过深（冗余嵌套）", "文档 2.1；可用 --dedupe 清理"),
    ("span-leaf", "span[leaf] 内含块级元素", "文档 2.2"),
    ("node-leaf", "section[nodeleaf] 结构不符规范", "文档 2.3"),
    ("redundant-node", "冗余空子节点过多", ""),
    ("darkmode-low-contrast", "文字与背景对比度太低", "文档 4.1.1"),
    ("darkmode-no-gradient", "文字背景使用了渐变", "文档 4.1.2"),
]

# ⛔ 规范里有、检测器**完全不查**的章节（既无函数也无可接入实现）。
#    这些只能靠生成阶段遵守（见 SOP `04-html.md` 的 R3/R4/R5）。
SPEC_ONLY_RULES = [
    ("3 字体使用规范", "不设置任何字体族", "函数存在但未接入"),
    ("4.2.1 背景容器", "多段共用背景应写公共容器", "无实现"),
    ("4.2.2 嵌套关系", "禁绝对定位等破坏结构顺序", "无独立实现（部分并入 nestNodes）"),
    ("4.3.1 / 4.4.1", "不要用图片承载纯文本", "无实现"),
    ("4.3.2 透明底图", "谨慎使用透明底色图片", "无实现"),
    ("4.3.3 补色机制", "背景图补色", "无实现"),
    ("4.5.2 !important", "不要使用 !important", "无实现"),
]

# 官方真实可用的三条命令（URL 抓取是 README 规划项，未实现）
OFFICIAL_CMDS = [
    ("check", "全规则检测（puppeteer 真机）", "pnpm check <file> [--json]"),
    ("dedupe", "清理冗余嵌套（jsdom 真删）", "pnpm dedupe <file> [--out=...] [--verify]"),
    ("probe", "环境探针（验证 puppeteer + 全规则跑通）", "pnpm probe"),
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


def _npx():
    """定位 npx。Windows 下是 npx.cmd，直接传 "npx" 会 WinError 2。"""
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    if npx:
        return npx
    for cand in (r"C:\Program Files\nodejs\npx.cmd",
                 os.path.join(os.environ.get("APPDATA", ""), "npm", "npx.cmd")):
        if os.path.isfile(cand):
            return cand
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
    npx = _npx()
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


# ---------------------------------------------------------------- dedupe（冗余嵌套清理）
def _split_shell(html):
    """把正文拆成 (前置外壳, 正文片段, 后置外壳)。

    官方 dedupe 只输出「正文片段」，会丢掉 <html>/<head>/<title>/<body>。
    本工具负责回填，保证输出与原件同一结构、可直接粘贴。
    """
    m = re.search(r"(.*?<body\b[^>]*>)", html, re.S | re.I)
    if not m:
        return None
    head = m.group(1)
    rest = html[m.end():]
    m2 = re.search(r"(</body\s*>\s*</html\s*>\s*)$", rest, re.S | re.I)
    if m2:
        return head, rest[:m2.start()], rest[m2.start():]
    m3 = re.search(r"(</body\s*>\s*)$", rest, re.S | re.I)
    if m3:
        return head, rest[:m3.start()], rest[m3.start():]
    return head, rest, ""


def visible_text(html):
    """可见文本（剔除 head/script/style 后剥标签、压缩空白）。

    这是判断 dedupe 是否安全的核心指标：清理冗余嵌套**不应改变任何可见字符**。
    """
    h = re.sub(r"<head\b.*?</head>", "", html, flags=re.S | re.I)
    h = re.sub(r"<(script|style)\b.*?</\1>", "", h, flags=re.S | re.I)
    h = re.sub(r"<[^>]+>", "", h)
    return re.sub(r"\s+", "", h)


def _run_node(cli, script, args, timeout=900):
    """统一调用 npx tsx <script> <args...>"""
    npx = _npx()
    if not npx:
        return None
    return subprocess.run([npx, "tsx", script] + list(args),
                          cwd=cli, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)


def run_dedupe(files, cli, dry_run=False):
    """调用官方 dedupe 清理冗余嵌套。

    权威值来自官方 `dedupe --verify`（内部跑 puppeteer 复测 before/after
    nestNodes 数）；安全判据是「可见文本逐字一致」。
    """
    runner = os.path.join(cli, "_wx_dedupe_runner.mjs")
    io.open(runner, "w", encoding="utf-8").write(DEDUPE_RUNNER)

    stamp = __import__("datetime").datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_root = os.path.join(workspace_root(), "_备份", "dedupe前_%s" % stamp)
    entries = []

    with tempfile.TemporaryDirectory() as td:
        for f in files:
            rel = os.path.relpath(f, workspace_root())
            e = {"file": f, "rel": rel, "ok": False, "err": "",
                 "written": None, "same_text": None, "nest": "(未知)",
                 "bytes": (0, 0)}
            orig = io.open(f, encoding="utf-8").read()
            src = os.path.join(td, "in.html")
            dst = os.path.join(td, "out.html")
            io.open(src, "w", encoding="utf-8", newline="").write(orig)
            if os.path.isfile(dst):
                os.remove(dst)

            # 官方 dedupe（--verify 会用 puppeteer 复测 nestNodes）
            r = _run_node(cli, "_wx_dedupe_runner.mjs", [src, dst, "--verify"])
            if r is None or not os.path.isfile(dst):
                e["err"] = "dedupe 失败：" + ((r.stderr if r else "") or "")[-160:]
                entries.append(e)
                continue

            # 官方把 verify 结果写 stderr（形如 "nestNodes: 4 → 0"）
            err = (r.stderr or "")
            m = re.search(r"nestNodes:\s*(\d+)\s*(?:→|->)\s*(\d+)", err)
            if m:
                e["nest"] = "%s → %s" % (m.group(1), m.group(2))

            cleaned = io.open(dst, encoding="utf-8").read()
            shell = _split_shell(orig)
            if shell:
                head, _, tail = shell
                inner = cleaned
                mi = re.search(r"<body\b[^>]*>(.*)$", cleaned, re.S | re.I)
                if mi:
                    inner = mi.group(1)
                inner = re.sub(r"</body\s*>\s*</html\s*>\s*$", "", inner,
                               flags=re.I | re.S)
                cleaned = head + inner + tail

            e["cleaned"] = cleaned
            e["ok"] = True
            e["same_text"] = visible_text(orig) == visible_text(cleaned)
            e["bytes"] = (len(orig.encode("utf-8")), len(cleaned.encode("utf-8")))
            entries.append(e)

    for e in entries:
        if not e["ok"] or dry_run:
            continue
        dst = e["file"]
        cur = io.open(dst, encoding="utf-8").read()
        if e["cleaned"] == cur:
            e["written"] = "unchanged"
            continue
        bp = os.path.join(backup_root, e["rel"])
        os.makedirs(os.path.dirname(bp), exist_ok=True)
        shutil.copy2(dst, bp)
        io.open(dst, "w", encoding="utf-8", newline="").write(e["cleaned"])
        e["written"] = "ok"

    return {"entries": entries, "backup": backup_root}


DEDUPE_RUNNER = r"""
// 冗余嵌套清理（调用官方 clean-runner；--verify 额外用 puppeteer 复测 nestNodes）
// 用法: npx tsx _wx_dedupe_runner.mjs <输入html> <输出html> [--verify]
import fs from 'node:fs';
import { runClean } from './src/clean-runner.ts';

const [, , inFile, outFile, flag] = process.argv;
const html = fs.readFileSync(inFile, 'utf8');
const cleaned = runClean(html);
fs.writeFileSync(outFile, cleaned, 'utf8');
console.log('CLEANED ' + outFile);

if (flag === '--verify') {
  try {
    const mod = await import('./src/clean-runner.ts');
    if (typeof mod.runCleanWithVerify === 'function') {
      const r = await mod.runCleanWithVerify(html);
      process.stderr.write('nestNodes: ' + r.before + ' \u2192 ' + r.after + '\n');
    }
  } catch (e) {
    process.stderr.write('verify skipped: ' + String(e).slice(0, 120) + '\n');
  }
}
"""


def report_dedupe(res, dry_run, args):
    base = workspace_root()
    entries = res["entries"]

    print()
    print("=" * 80)
    print("  官方 dedupe 冗余嵌套清理 · %s · 共 %d 篇" %
          ("预览（未改动）" if dry_run else "已写回", len(entries)))
    print("=" * 80)
    print()
    print("  %-38s %-12s %-8s %s" % ("文件", "nestNodes", "文本一致", "结果"))
    print("  " + "-" * 74)
    n_fixed = n_unsafe = 0
    for e in entries:
        name = e["rel"][-38:]
        if not e["ok"]:
            print("  %-38s %-12s %-8s %s" % (name, "—", "—", "✗ " + e["err"][:50]))
            continue
        same = "✅" if e["same_text"] else "❌"
        if not e["same_text"]:
            n_unsafe += 1
        note = ("预览" if dry_run else
                ("无变化" if e["written"] == "unchanged" else "已写回"))
        print("  %-38s %-12s %-8s %s" % (name, e["nest"], same, note))
        if e["nest"] not in ("(未知)",) and "→" in e["nest"]:
            try:
                a, b = e["nest"].split("→")
                if int(b) < int(a):
                    n_fixed += 1
            except ValueError:
                pass
    print()
    print("  nestNodes 减少：%d 篇" % n_fixed)
    if n_unsafe:
        print("  ⛔ 可见文本有变化的篇数：%d（**不应写回**，请人工核查）" % n_unsafe)
    else:
        print("  ✅ 全部篇目「可见文本逐字一致」——清理安全")
    if not dry_run and any(e.get("written") == "ok" for e in entries):
        print("  备份：%s" % os.path.relpath(res["backup"], base))
    print("  说明：原件 <html>/<head>/<title>/<body> 外壳已自动回填；")
    print("        <br> → <br/> 等格式归一属 HTML 等价，不影响显示。")
    print()


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
    ap.add_argument("--setup", action="store_true", help="环境准备自检（跑官方探针，验证 puppeteer + 全规则）")
    ap.add_argument("--list-rules", action="store_true", help="列出官方支持的规则")
    ap.add_argument("--dedupe", metavar="FILE", nargs="+",
                    help="清理冗余嵌套（治 nestNodes）；自动备份 + 回填 <html>/<head> 外壳")
    ap.add_argument("--dry-run", action="store_true",
                    help="配合 --dedupe：只预览清理效果，不写回文件")
    args = ap.parse_args()

    if args.list_rules:
        print("官方检测器支持的规则（%d 条）：" % len(OFFICIAL_RULES))
        print()
        for k, name, note in OFFICIAL_RULES:
            print("  %-26s %s%s" % (k, name, ("　← " + note) if note else ""))
        print()
        print("─" * 78)
        print("  ⛔ 规范里有、检测器**完全不查**的章节（%d 条）—— 只能靠生成阶段遵守"
              % len(SPEC_ONLY_RULES))
        print("─" * 78)
        for chap, name, why in SPEC_ONLY_RULES:
            print("  %-18s %-30s %s" % (chap, name, why))
        print()
        print("  ⇒ 「官方检测通过」≠「符合文档」。生成阶段规则见 SOP `04-html.md` 的 R1–R5。")
        print()
        print("─" * 78)
        print("  官方真实可用的命令（%d 条；URL 抓取是 README 规划项，未实现）" % len(OFFICIAL_CMDS))
        print("─" * 78)
        for name, desc, usage in OFFICIAL_CMDS:
            print("  %-10s %-34s %s" % (name, desc, usage))
        print()
        print("  ⚠️ 唯一「函数已实现但未接入」的是 checkFontFamilyViolation（调用 0 次）；")
        print("     其余 8 个 check* 函数均已接入。其余未查项是**根本没有实现**。")
        return

    cli = ensure_tool()
    if not cli:
        sys.exit(2)

    if args.setup:
        print("  ✅ 官方工具可用：%s" % cli)
        print()
        print("  跑官方探针（puppeteer + 注入 bundle + 全规则含布局类）...")
        r = subprocess.run([_npx(), "tsx", "src/probe.ts"], cwd=cli,
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=600)
        out = (r.stdout or "") + (r.stderr or "")
        if "探针通过" in out:
            print("  ✅ 探针通过（全规则含布局类跑通）")
        else:
            print("  ⚠️ 探针未确认通过，输出尾部：")
            print("    " + out[-500:].replace("\n", "\n    "))
        return

    if args.dedupe:
        files = [os.path.abspath(f) for f in args.dedupe]
        miss = [f for f in files if not os.path.isfile(f)]
        if miss:
            print("  ✗ 文件不存在：%s" % miss[:3])
            sys.exit(1)
        if not args.dry_run:
            print("  ⚠️ 将写回 %d 篇正文（写前自动备份到 _备份/dedupe前_<时间戳>/）" % len(files))
        res = run_dedupe(files, cli, dry_run=args.dry_run)
        if res is None:
            sys.exit(1)
        report_dedupe(res, args.dry_run, args)
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
