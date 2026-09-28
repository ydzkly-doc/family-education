# -*- coding: utf-8 -*-
"""口播感检查（台词与金句）——只读。

⚠️ 先读定位，别误用：
    这是 SOP「出声朗读测」的 **第①层（机械筛）**，**不是替代品**。
    - 它能筛：超长分句 / 书面连接词串联 / 四六工整顺口溜——**机械可判的部分**；
    - 它筛不出：「话说得对不对味」——例如"我反而想恭喜你长大了"，
      字面并不长、连接词也没有，**但现实中张不开嘴**。
    → 第②层（agent 复读，**有系统性盲区**）与第③层（**人出声念，唯一权威**）不可省。
    详见 SOP `skills/wechat-sop/references/02-writing.md`「出声朗读测」。

用法：
    PY="C:/Users/ZhuanZ/.workbuddy/binaries/python/versions/3.13.12/python.exe"
    "$PY" 工具脚本/check_spoken.py "手机方案/公众号文章"
    "$PY" 工具脚本/check_spoken.py <目录或文件…> --max-len 15 --examples 6
"""
import argparse
import glob
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

# ---- 切句 ----
SPLIT_MAJOR = re.compile(r"[。！？；!?;]")
SPLIT_MINOR = re.compile(r"[，、,]")
# ---- 书面连接词（口语里很少连续出现）----
CONNECTORS = ["因为", "由于", "还是", "但是", "然而", "因此", "所以", "并且",
              "于是", "虽然", "如果", "不仅", "而且", "不过", "既然", "即使", "同时"]
# ---- 提取 ----
PARA_RE = re.compile(r"<p\b[^>]*>(.*?)</p>", re.S)
BOLD_RE = re.compile(r"<(?:b|strong)\b[^>]*>(.*?)</(?:b|strong)>", re.S)
TAG_RE = re.compile(r"<[^>]+>")
QUOTE_RE = re.compile(r"[“\"]([^“”\"]{6,})[”\"]")


def strip_tags(s: str) -> str:
    return TAG_RE.sub("", s).replace("&nbsp;", " ").strip()


def split_clauses(text: str):
    out = []
    for major in SPLIT_MAJOR.split(text):
        for minor in SPLIT_MINOR.split(major):
            c = strip_tags(minor).strip("“”\"'（）()　 ")
            if c:
                out.append(c)
    return out


def has_parallel(clauses, need=3) -> bool:
    """连续 need 个分句字数完全相同 → 疑似工整顺口溜。"""
    run, prev = 1, None
    for c in clauses:
        n = len(c)
        if prev is not None and n == prev:
            run += 1
            if run >= need:
                return True
        else:
            run = 1
        prev = n
    return False


def collect(html: str, skip_marks=("来源声明", "阅读说明", "说明：")):
    """→ (台词列表, 金句列表)，均排除说明/声明段。

    ⚠️ 引号必须在**去标签后的纯文本**里找——否则会匹配到 HTML 属性
    （`style="display:inline-block…"`），把样式串当成台词（2026-09-28 实测踩到）。
    """
    lines, bolds = [], []
    for m in PARA_RE.finditer(html):
        raw = m.group(1)
        txt = strip_tags(raw)
        if any(k in txt for k in skip_marks):
            continue
        for q in QUOTE_RE.findall(txt):           # ← 在纯文本里找，不在 raw 里
            q = q.strip()
            if len(q) >= 6 and "→" not in q:       # 箭头链（"难受→刷屏→…"）不是台词
                lines.append(q)
        if "<b>" in raw or "<b " in raw or "<strong>" in raw:
            for b in BOLD_RE.findall(raw):
                b = strip_tags(b).strip()
                if len(b) >= 12:
                    bolds.append(b)
    return lines, bolds


def check(items, max_len, use_connectors=True):
    """→ [(原句, 最长分句字数, [问题标签])]

    ⚠️ 连接词只对**台词**测：SOP 的"口语化三条"约束的是"要照念的父母台词"；
    金句是"可独立截图的一句话"，本就偏书面，套台词标准会大量误报。
    """
    bad = []
    for it in items:
        cs = split_clauses(it)
        if not cs:
            continue
        longest = max(len(c) for c in cs)
        tags = []
        if longest > max_len:
            tags.append(f"最长分句 {longest} 字 > {max_len}")
        hit = [c for c in CONNECTORS if c in it]
        if use_connectors and len(cs) >= 2 and hit:
            tags.append("书面连接词 " + "/".join(hit))
        if has_parallel(cs):
            tags.append("疑似工整对仗（连续同字数分句）")
        if tags:
            bad.append((it, longest, tags))
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+", help="目录或文件")
    ap.add_argument("--max-len", type=int, default=15, help="分句字数上限（默认 15）")
    ap.add_argument("--examples", type=int, default=5, help="每篇最多列几条")
    a = ap.parse_args()

    files = []
    for raw in a.paths:
        if os.path.isdir(raw):
            files += glob.glob(os.path.join(raw, "**", "正文_*.html"), recursive=True)
        elif os.path.isfile(raw):
            files.append(raw)
    files = sorted(set(f for f in files if "_备份" not in f),
                   key=lambda p: int(re.search(r"第(\d+)篇", p).group(1))
                   if re.search(r"第(\d+)篇", p) else 999)
    if not files:
        print("未找到 正文_*.html")
        return 1

    print("=" * 74)
    print(f"口播感检查（第①层·机械筛）  文件 {len(files)} 个  分句上限 {a.max_len} 字")
    print("⛔ 通过 ≠ 念得出口——「话说得对不对味」这一层脚本测不出，最后一遍必须人工出声念。")
    print("=" * 74)

    t_all = b_all = t_bad = b_bad = 0
    for f in files:
        html = open(f, encoding="utf-8", errors="ignore").read()
        lines, bolds = collect(html)
        t_all += len(lines)
        b_all += len(bolds)
        bl = check(lines, a.max_len)
        bb = check(bolds, a.max_len, use_connectors=False)
        t_bad += len(bl)
        b_bad += len(bb)
        if not bl and not bb:
            continue
        name = re.search(r"正文_(第\d+篇_[^.]+)\.html", f)
        print(f"\n【{name.group(1) if name else os.path.basename(f)}】"
              f"台词 {len(lines)} 条 / 金句 {len(bolds)} 条")
        for label, items in (("台词", bl), ("金句", bb)):
            for it, longest, tags in items[: a.examples]:
                print(f"  ⚠ {label}（{longest} 字）｜{'；'.join(tags)}")
                print(f"     「{it[:52]}{'…' if len(it) > 52 else ''}」")
            if len(items) > a.examples:
                print(f"  … 另有 {len(items) - a.examples} 条，略")

    print("\n" + "=" * 74)
    print(f"汇总：台词 {t_all} 条（{t_bad} 条待人工确认）｜金句 {b_all} 条（{b_bad} 条待人工确认）")
    print("命中＝**筛出来让你看**，不等于一定错；改不改由人定。")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())
