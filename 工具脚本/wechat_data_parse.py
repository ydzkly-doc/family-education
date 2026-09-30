#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
wechat_data_parse.py —— 只读解析「微信公众号后台 · 单篇数据明细」导出的 .xls

用途
    公众号后台导出的 `数据明细（篇名）.xls` 是老式 BIFF/.xls（OLE2 复合文档，
    文件头 d0cf11e0），**普通文本工具读不了**；也常因本地表格编辑器服务
    （127.0.0.1:39099）掉线而开不了。本脚本用 xlrd **纯只读**解析，不写回任何文件。

    ⭐ 本表是**分节结构**，不是规整表格：
        标题
        ├ 数据概况         （数据指标 | 数值）
        ├ 阅读转化         （数据指标 | 数值）
        ├ 阅读数据趋势明细 （日期 | 传播渠道 | 阅读人数 | 分享人数）
        ├ 性别分布 / 年龄分布 / 地域分布
    所以读取必须**先切节、再取值**，不能当成一张平表。

用法
    python 工具脚本/wechat_data_parse.py <目录或文件...>              # 原始 dump（逐节列出）
    python 工具脚本/wechat_data_parse.py <目录> --table               # ⭐ 紧凑汇总表（一篇一行）
    python 工具脚本/wechat_data_parse.py <目录> --diff                # 逐对语义差异比对
    python 工具脚本/wechat_data_parse.py <目录> --json out.json       # 结构化输出

配对规则
    文件名去掉结尾 " (1)" / "(2)" 后相同者视为同一篇的两份。

⛔ 差异判据是**单元格值本身**，不是文件大小／md5：
    Excel 元数据（作者、保存时间）变化会让 md5 不同，但数据可能完全一致。**只看值。**
"""
import argparse
import glob
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

try:
    import xlrd
except ImportError:
    print("[缺依赖] 请先装 xlrd：")
    print('  "C:/Users/ZhuanZ/.workbuddy/binaries/python/envs/default/Scripts/pip.exe" install xlrd')
    sys.exit(2)

PAIR_TAIL = re.compile(r"\s*\((\d+)\)\s*$")
# 这些是分节标题（单格行）；其余单格行视为文章标题
KNOWN_SECTIONS = ("数据概况", "阅读转化", "阅读数据趋势明细", "性别分布", "年龄分布", "地域分布")
# 表头词：出现这些当作表头，不当数据
HEADER_WORDS = {"数据指标", "数值", "日期", "传播渠道", "阅读人数", "分享人数",
                "性别", "年龄", "省份/直辖市", "占比"}


def strip_pair_tail(name):
    base, ext = os.path.splitext(name)
    return PAIR_TAIL.sub("", base) + ext


def collect(targets):
    files = []
    for t in targets:
        if os.path.isdir(t):
            files.extend(glob.glob(os.path.join(t, "*.xls")))
            files.extend(glob.glob(os.path.join(t, "*.xlsx")))
        elif os.path.isfile(t):
            files.append(t)
        else:
            print(f"[跳过] 不存在：{t}")
    return sorted(set(files))


def norm(v):
    """单元格值归一：整数去掉 .0，字符串去空白。"""
    if isinstance(v, float) and v.is_integer():
        return int(v)
    if isinstance(v, str):
        return v.strip()
    return v


def read_sheet(path):
    book = xlrd.open_workbook(path)
    sh = book.sheet_by_index(0)
    rows = []
    for r in range(sh.nrows):
        row = [norm(sh.cell_value(r, c)) for c in range(sh.ncols)]
        while row and row[-1] == "":
            row.pop()
        rows.append(row)
    return rows


def parse_detail(path):
    """把分节结构解析成 dict。"""
    rows = read_sheet(path)
    out = {"_file": os.path.basename(path), "_size": os.path.getsize(path),
           "_rows": len(rows), "标题": "", "节": {}}
    cur = None
    section = None
    for row in rows:
        cells = [c for c in row if c != ""]
        if not cells:
            continue
        if len(cells) == 1:
            name = cells[0]
            if name in KNOWN_SECTIONS:
                section = name
                cur = out["节"].setdefault(name, [])
            elif not out["标题"]:
                out["标题"] = name
            else:
                section = name
                cur = out["节"].setdefault(name, [])
            continue
        if cur is not None:
            # ⚠️ 本表**第 0 列是空列**，数据从第 1 列起 → 必须用「滤掉空格后的 cells」，
            #    否则整行会左移一位，取到的是上一列的值（曾因此全部取成 None / 错位）。
            cur.append(cells)
    return out


def kv(section_rows):
    """把「数据指标|数值」两列节转成 dict（跳过表头行）。"""
    d = {}
    for row in section_rows:
        if len(row) >= 2 and row[0] not in HEADER_WORDS:
            d[str(row[0])] = row[1]
    return d


def as_int(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


def trend(section_rows):
    rows = [r for r in section_rows
            if len(r) >= 4 and r[0] not in HEADER_WORDS]
    return [{"日期": r[0], "渠道": r[1], "阅读": r[2], "分享": r[3]} for r in rows]


def pct(section_rows):
    d = {}
    for row in section_rows:
        if len(row) >= 2 and row[0] not in HEADER_WORDS:
            d[str(row[0])] = row[1]
    return d


def metrics(detail):
    """抽出对复盘有价值的指标。"""
    m = {}
    g = kv(detail["节"].get("数据概况", []))
    c = kv(detail["节"].get("阅读转化", []))
    m["阅读"] = g.get("阅读(人)")
    m["停留"] = g.get("平均停留时长(秒)")
    m["完读率"] = g.get("完读率")
    m["分享"] = g.get("分享(人)")
    m["在看"] = g.get("在看(人)")
    m["点赞"] = g.get("点赞(人)")
    m["收藏"] = g.get("收藏(人)")
    m["评论"] = g.get("评论（条）")
    m["新关注"] = g.get("新增关注（人）")
    m["听全文"] = g.get("听全文（人）")
    m["送达"] = c.get("送达人数")
    m["公众号消息阅读"] = c.get("公众号消息阅读人数")
    m["分享产生阅读"] = c.get("分享产生的阅读人数")
    # 载体判据：有「完读率」字段 = 长文版；无 = 卡片版
    m["载体"] = "长文版" if g.get("完读率") not in (None, "") else "卡片版"
    return m


def channels(detail):
    """从趋势明细汇总渠道构成（只取「全部」以外的渠道行）。"""
    t = trend(detail["节"].get("阅读数据趋势明细", []))
    tot = {}
    overall = 0
    ok = 0
    for r in t:
        if r["渠道"] == "全部":
            overall += as_int(r["阅读"])
        else:
            tot[r["渠道"]] = tot.get(r["渠道"], 0) + as_int(r["阅读"])
    return tot, overall


def show_dump(files):
    for f in files:
        d = parse_detail(f)
        print("=" * 78)
        print(f"文件：{d['_file']}   （{d['_size']} 字节）")
        print("=" * 78)
        print(f"标题：{d['标题']}")
        for name in KNOWN_SECTIONS:
            rows = d["节"].get(name)
            if not rows:
                continue
            print(f"\n--- {name} ---")
            for row in rows:
                print("   " + " | ".join(str(x) for x in row))
        print()


def show_table(files):
    hdr = ["标题", "载体", "阅读", "停留", "完读率", "分享", "在看", "点赞", "收藏",
           "评论", "新关注", "送达", "分享产生阅读", "渠道构成"]
    print(" | ".join(hdr))
    print("-" * 160)
    for f in files:
        d = parse_detail(f)
        m = metrics(d)
        ch, _ = channels(d)
        chs = "／".join(f"{k}{v}" for k, v in sorted(ch.items(), key=lambda kv: -kv[1]))
        fr = m["完读率"]
        fr = f"{float(fr)*100:.1f}%" if isinstance(fr, (int, float)) else (fr or "")
        print(" | ".join(str(x) for x in [
            d["标题"][:22], m["载体"], m["阅读"], m["停留"], fr, m["分享"], m["在看"],
            m["点赞"], m["收藏"], m["评论"], m["新关注"], m["送达"],
            m["分享产生阅读"], chs or "—"]))


def show_diff(files):
    groups = {}
    for f in files:
        groups.setdefault(strip_pair_tail(os.path.basename(f)), []).append(f)
    print("=" * 78)
    print("逐对语义差异比对（按「指标→值」比对，不受行号错位影响）")
    print("=" * 78)
    for key, fs in sorted(groups.items()):
        if len(fs) < 2:
            print(f"\n▌{key}\n    （只有 1 份，无配对）")
            continue
        print(f"\n▌{key}   共 {len(fs)} 份")
        parsed = [parse_detail(f) for f in fs]
        for f, d in zip(fs, parsed):
            print(f"    · {os.path.basename(f)}  {d['_size']} 字节 / {d['_rows']} 行")
        # 收集全部指标键
        maps = [metrics(d) for d in parsed]
        keys = []
        for m in maps:
            for k in m:
                if k not in keys:
                    keys.append(k)
        diffs = []
        for k in keys:
            vals = [m.get(k) for m in maps]
            if len(set(map(str, vals))) > 1:
                diffs.append((k, vals))
        same_struct = len({d["_rows"] for d in parsed}) == 1
        if not diffs:
            print("    → ✅ **数据完全一致**（同一份重复下载；文件大小/md5 可能因元数据不同）")
        else:
            print(f"    → ❌ **数据不同**（{len(diffs)} 个指标有差异）")
            for k, vals in diffs:
                print(f"         {k:<14} " + "  vs  ".join(str(v) for v in vals))
        # 渠道差异
        chs = [channels(d)[0] for d in parsed]
        if any(c != chs[0] for c in chs[1:]):
            print("         【渠道构成不同】")
            for f, c in zip(fs, chs):
                print(f"           {os.path.basename(f)[:38]:<40} {c}")


def main():
    ap = argparse.ArgumentParser(
        description="只读解析微信公众号「数据明细」.xls（分节结构）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("配对规则")[0],
    )
    ap.add_argument("targets", nargs="+", help="目录或 .xls 文件")
    ap.add_argument("--table", action="store_true", help="紧凑汇总表（一篇一行）")
    ap.add_argument("--diff", action="store_true", help="逐对语义差异比对")
    ap.add_argument("--json", metavar="OUT", help="结构化输出到 JSON")
    args = ap.parse_args()

    files = collect(args.targets)
    if not files:
        print("没有找到任何 .xls 文件")
        return 1
    print(f"共 {len(files)} 个文件\n")

    if args.json:
        data = {}
        for f in files:
            try:
                d = parse_detail(f)
                d["_指标"] = metrics(d)
                d["_渠道"] = channels(d)[0]
                data[os.path.basename(f)] = d
            except Exception as e:
                data[os.path.basename(f)] = {"__error__": f"{type(e).__name__}: {e}"}
        with open(args.json, "w", encoding="utf-8") as fp:
            json.dump(data, fp, ensure_ascii=False, indent=2)
        print(f"已写入 {args.json}\n")

    if args.table:
        show_table(files)
        print()
    if args.diff:
        show_diff(files)
    elif not args.table and not args.json:
        show_dump(files)
    return 0


if __name__ == "__main__":
    sys.exit(main())
