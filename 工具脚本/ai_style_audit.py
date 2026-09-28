# -*- coding: utf-8 -*-
"""
全库正文「AI 味」体检（只读，不改动任何文件）

把「感觉这批文章很像 AI 写的」这种主观判断，变成可复核、可追踪的数字。
输出：篇数/系列数、开篇时间戳命中率、冲突开场率、顿悟句式率、
      「不是…而是」密度、结尾模板覆盖率、打卡模板覆盖率、端水句密度。

用法：
    python ai_style_audit.py
    python ai_style_audit.py --root "D:\\个人资料\\家庭教育" --head 300 --top 12
"""
import re
import sys
import argparse
from pathlib import Path
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding="utf-8")

TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.S | re.I)
ENT = {
    "&nbsp;": " ", "&amp;": "&", "&quot;": '"', "&ldquo;": "“",
    "&rdquo;": "”", "&mdash;": "—", "&hellip;": "…", "&lt;": "<", "&gt;": ">",
}


def to_text(html: str) -> str:
    t = SCRIPT_RE.sub("", html)
    t = TAG_RE.sub("\n", t)
    for k, v in ENT.items():
        t = t.replace(k, v)
    t = re.sub(r"[ \t\u3000]+", "", t)
    t = re.sub(r"\n{2,}", "\n", t)
    return t.strip()


def flat(t: str) -> str:
    return re.sub(r"\s+", "", t)


# ---------- 检测规则 ----------
TIME_RE = re.compile(
    r"[零一二两三四五六七八九十\d]{1,3}点(?:[零一二三四五六七八九十\d]{1,3}分|半)"
    r"|(?:凌晨|晚上|夜里|深夜|半夜)[零一二两三四五六七八九十\d]{1,3}点"
    r"|\d{1,2}\s*[:：]\s*\d{2}"
)
CONFLICT_RE = re.compile(r"摔门|反锁|砰|抢过手机|把路由器|夺手机|落锁")
EPIPHANY_RE = re.compile(
    r"点醒|愣住|扎了我一下|扎得我|扎了我|突然明白|回过味来|忽然懂了|突然懂了"
    r"|当场笑不出|脑子嗡|像被电了一|才明白过来"
)
NOTBUT_RE = re.compile(
    r"不是[^。！？；\n]{0,30}?而是|不只是[^。！？；\n]{0,30}?更是"
    r"|不但[^。！？；\n]{0,30}?而且|与其说[^。！？；\n]{0,30}?不如说"
)
ENDING_RE = re.compile(r"还在重启的爸爸|一个也在重启的父亲|重启的爸爸|同路人")
TEMPLATE_RE = re.compile(r"我家在用|七天|7天|打卡|观察表|一天一张表")
HEDGE_RE = re.compile(r"因人而异|因家庭而异|不意味着|但这并不|并不能说|不一定适用|不是每个家庭")


def series_of(p: Path, root: Path) -> str:
    try:
        parts = p.relative_to(root).parts
    except ValueError:
        return "?"
    if parts[0] == "王金海讲书" and len(parts) > 1:
        return "王金海讲书/" + parts[1]
    return parts[0]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=r"D:\个人资料\家庭教育")
    ap.add_argument("--head", type=int, default=300, help="开篇检查字数")
    ap.add_argument("--top", type=int, default=12, help="系列榜显示条数")
    args = ap.parse_args()

    root = Path(args.root)
    files = sorted(
        p for p in root.rglob("正文_*.html")
        if not any(x in p.parts for x in ("_备份", ".git", "node_modules", "_旧版本"))
    )
    if not files:
        print("未找到 正文_*.html")
        return

    n = len(files)
    hit = defaultdict(int)
    per_series = defaultdict(Counter)
    openers = []
    notbut_hist = Counter()
    epiphany_examples = []

    for p in files:
        try:
            raw = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        txt = to_text(raw)
        f = flat(txt)
        head = f[: args.head]
        s = series_of(p, root)

        t_hit = bool(TIME_RE.search(head))
        c_hit = bool(CONFLICT_RE.search(f))
        e_hit = bool(EPIPHANY_RE.search(f))
        end_hit = bool(ENDING_RE.search(f))
        tpl_hit = bool(TEMPLATE_RE.search(f))
        hd_hit = bool(HEDGE_RE.search(f))
        nb_cnt = len(NOTBUT_RE.findall(f))
        notbut_hist[min(nb_cnt, 6)] += 1

        for flag, key in (
            (t_hit, "开篇时间戳"), (c_hit, "冲突动作"), (e_hit, "顿悟句式"),
            (end_hit, "结尾模板"), (tpl_hit, "打卡/工具模板"), (hd_hit, "端水句"),
            (nb_cnt > 0, "不是A而是B"),
        ):
            if flag:
                hit[key] += 1
                per_series[s][key] += 1

        if t_hit:
            m = TIME_RE.search(head)
            openers.append((s, p.parent.name[:26], m.group(0) if m else ""))
        if e_hit and len(epiphany_examples) < 6:
            m = EPIPHANY_RE.search(f)
            i = m.start()
            epiphany_examples.append(f[max(0, i - 14): i + 16])

    print("=" * 68)
    print("全库正文 AI 味体检   |   篇数 %d   |   系列数 %d" % (n, len(per_series)))
    print("=" * 68)
    rows = [
        ("开篇时间戳", "开篇 %d 字内出现分钟级时间" % args.head),
        ("冲突动作", "全文出现 摔门/反锁/砰/夺手机"),
        ("顿悟句式", "全文出现 点醒/愣住/扎了我一下/忽然懂了"),
        ("不是A而是B", "全文出现 ≥1 次"),
        ("打卡/工具模板", "我家在用/7天/打卡/观察表"),
        ("端水句", "因人而异/不意味着/不一定适用"),
        ("结尾模板", "还在重启的爸爸/同路人"),
    ]
    for key, desc in rows:
        c = hit[key]
        bar = "#" * int(round(c / n * 24))
        print("  %-14s %3d/%d  %5.1f%%  %-24s %s" % (key, c, n, c / n * 100, bar, desc))

    print("-" * 68)
    print("「不是…而是」每篇出现次数分布（0 视为未命中）：")
    for k in sorted(notbut_hist):
        label = "%d 次" % k if k < 6 else "6+ 次"
        print("      %-6s %3d 篇" % (label, notbut_hist[k]))
    tot_nb = sum(k * v for k, v in notbut_hist.items())
    print("      平均 %.2f 次/篇" % (tot_nb / n))

    print("-" * 68)
    print("开篇时间戳命中的篇目（共 %d 篇，看位置分布）：" % len(openers))
    for s, folder, frag in openers:
        print("      [%-16s] %-26s %s" % (s, folder, frag))

    print("-" * 68)
    print("顿悟句式样例（截取命中处前后各若干字）：")
    for ex in epiphany_examples:
        print("      …%s…" % ex)

    print("-" * 68)
    print("按系列看命中密度（Top %d，按命中总项排序）：" % args.top)
    ranked = sorted(per_series.items(), key=lambda kv: -sum(kv[1].values()))
    for s, cnt in ranked[: args.top]:
        print("      %-20s 命中 %2d 项   %s" % (s, sum(cnt.values()), dict(cnt)))
    print("=" * 68)


if __name__ == "__main__":
    main()
