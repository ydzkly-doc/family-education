# -*- coding: utf-8 -*-
"""句式 / 关键词「定位」工具（只读，改稿专用）。

为什么要有它：
    模板感诊断（template_scan.py）只报「第 N 篇命中 X 次」，
    **报不出是哪一句**——而改稿时必须看到原句才能替换，只看计数等于盲改。

用法：
    PY="C:/Users/ZhuanZ/.workbuddy/binaries/python/versions/3.13.12/python.exe"
    "$PY" 工具脚本/locate_pattern.py <目录或文件…>
    "$PY" 工具脚本/locate_pattern.py <目录> --pattern "不是[^。]{1,30}?而是" --span 20

默认句式：「不是…而是…」「不只是…更是…」
（即 SOP `02-writing.md`「句式节流」条的配额对象）
"""
import argparse
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

DEFAULT_PATTERN = r"不是[^。！？；\n]{1,30}?而是|不只是[^。！？；\n]{1,30}?更是"
TAG_RE = re.compile(r"<[^>]+>")


def visible(html: str) -> str:
    """去 head/script/style/标签，得到可见文字（与 template_scan 口径一致）。

    ⚠️ 去 <head> 是为了排除 <title>——标题句式不算正文配额。
    """
    t = re.sub(r"<head\b.*?</head>", "", html, flags=re.S | re.I)
    t = re.sub(r"<(script|style)\b.*?</\1>", "", t, flags=re.S | re.I)
    return TAG_RE.sub("", t)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+", help="文件或目录")
    ap.add_argument("--pattern", default=DEFAULT_PATTERN)
    ap.add_argument("--span", type=int, default=16, help="命中处前后各取多少字")
    ap.add_argument("--ext", default=".html", help="扫描的扩展名（默认 .html）")
    a = ap.parse_args()

    pat = re.compile(a.pattern)
    files = []
    for raw in a.paths:
        p = Path(raw)
        if p.is_dir():
            files += sorted(p.rglob("*" + a.ext))
        elif p.is_file():
            files.append(p)
    files = [f for f in files if "_备份" not in str(f)]

    total = 0
    for f in files:
        txt = visible(f.read_text(encoding="utf-8", errors="ignore"))
        hits = list(pat.finditer(txt))
        if not hits:
            continue
        total += len(hits)
        print(f"\n=== {f.name} ｜ 命中 {len(hits)} 次 ===")
        for i, m in enumerate(hits, 1):
            s, e = m.start(), m.end()
            print(f"  {i}. …{txt[max(0, s - a.span):s]}〖{m.group(0)}〗{txt[e:e + a.span]}…")
    print(f"\n合计命中 {total} 次（扫描 {len(files)} 个文件）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
