# -*- coding: utf-8 -*-
"""统计外部文章的字数（只读网页、**不保存正文内容**）。

用途：拿真实样本校准「我们该写多长」——外部爆款 vs 本账号正文。
⚠️ 本脚本只输**字数/段数**，不落地正文（版权）。

用法：
    PY="C:/Users/ZhuanZ/.workbuddy/binaries/python/versions/3.13.12/python.exe"
    "$PY" 工具脚本/fetch_article_len.py "https://…" "https://…"
    "$PY" 工具脚本/fetch_article_len.py --from-file urls.txt

判据说明：
    正文启发式 = 取 <p> 段落中 ≥20 字的那些求和（滤掉导航/相关阅读/版权行）。
    中文字数只数 CJK 字符（不含标点、数字、英文）——与 `模板感诊断 --count` 同口径。
"""
import argparse
import re
import sys
from urllib.request import Request, urlopen

sys.stdout.reconfigure(encoding="utf-8")

CJK = re.compile(r"[\u4e00-\u9fff]")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def fetch(url: str) -> str:
    req = Request(url, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})
    raw = urlopen(req, timeout=30).read()
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")


def article_len(html: str):
    """→ (中文字数, 段数)。启发式取 <p> 里 ≥20 字的段。"""
    h = re.sub(r"<(script|style)\b.*?</\1>", "", html, flags=re.S | re.I)
    total, n = 0, 0
    for p in re.findall(r"<p\b[^>]*>(.*?)</p>", h, re.S):
        t = re.sub(r"<[^>]+>", "", p)
        t = re.sub(r"\s", "", t).replace("&nbsp;", "")
        if len(t) >= 20:
            total += len(CJK.findall(t))
            n += 1
    return total, n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("urls", nargs="*")
    ap.add_argument("--from-file", help="每行一个 URL")
    a = ap.parse_args()

    urls = list(a.urls)
    if a.from_file:
        urls += [x.strip() for x in open(a.from_file, encoding="utf-8")
                 if x.strip() and not x.startswith("#")]
    if not urls:
        print("未提供 URL")
        return 1

    ok = []
    for i, u in enumerate(urls, 1):
        try:
            n, seg = article_len(fetch(u))
            ok.append(n)
            print(f"[{i:>2}] {n:>6} 字  （{seg:>3} 段）  {u[:78]}")
        except Exception as e:  # noqa: BLE001
            print(f"[{i:>2}]   失败      {type(e).__name__}: {str(e)[:50]}  {u[:60]}")

    if ok:
        ok.sort()
        mid = ok[len(ok) // 2] if len(ok) % 2 else (ok[len(ok) // 2 - 1] + ok[len(ok) // 2]) // 2
        print("-" * 92)
        print(f"样本 {len(ok)} 篇 ｜ 最短 {ok[0]} ｜ 中位 {mid} ｜ 最长 {ok[-1]} ｜ "
              f"平均 {sum(ok) // len(ok)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
