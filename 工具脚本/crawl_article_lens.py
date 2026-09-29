# -*- coding: utf-8 -*-
"""批量抓取家庭教育类文章并统计字数（从种子页 BFS 扩展同站相关文章）。

⚠️ 只统计**字数/段数**，不保存、不复制正文（版权）。抓取限速、有上限。

用法：
    PY="C:/Users/ZhuanZ/.workbuddy/binaries/python/versions/3.13.12/python.exe"
    "$PY" 工具脚本/crawl_article_lens.py --target 100
    "$PY" 工具脚本/crawl_article_lens.py --target 100 --per-host 35 --delay 0.4
"""
import argparse
import re
import sys
import time
from collections import deque
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

sys.stdout.reconfigure(encoding="utf-8")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

SEEDS = [
    "https://new.qq.com/rain/a/20260920A0595G00",
    "https://new.qq.com/rain/a/20260818A08DVT00",
    "https://news.qq.com/rain/a/20260810A01QFM00",
    "https://www.sohu.com/a/1015553124_122648268",
    "https://www.sohu.com/a/1026199182_121106991",
    "https://www.sohu.com/a/1054526917_121106994",
    "https://m.sohu.com/a/1054174240_121686729",
    "https://www.163.com/dy/article/L59NE56D0514CJV0.html",
    "https://www.163.com/dy/article/L53SDCMR0530KB7U.html",
    "https://new.qq.com/rain/a/20250525A05X8Y00",
]

CJK = re.compile(r"[\u4e00-\u9fff]")


def fetch(url, timeout=20):
    req = Request(url, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})
    raw = urlopen(req, timeout=timeout).read()
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")


def article_len(html):
    """→ (中文字数, 段数, 标题)。标题用于**主题过滤**。"""
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
    title = re.sub(r"\s", "", m.group(1)) if m else ""
    h = re.sub(r"<(script|style)\b.*?</\1>", "", html, flags=re.S | re.I)
    total, n = 0, 0
    for p in re.findall(r"<p\b[^>]*>(.*?)</p>", h, re.S):
        t = re.sub(r"<[^>]+>", "", p)
        t = re.sub(r"\s", "", t).replace("&nbsp;", "")
        if len(t) >= 20:
            total += len(CJK.findall(t))
            n += 1
    return total, n, title


# ⚠️ 递归扩展会跑到体育/财经/汽车频道（实测踩过：URL 里出现 /sports/ /money/ /auto/），
#    故必须用**标题关键词**过滤主题，否则样本被污染。
TOPIC = re.compile(r"孩子|家长|父母|教育|育儿|青春|小学|初中|高中|学习|手机|老师|"
                   r"成长|亲子|妈妈|爸爸|儿子|女儿|叛逆|成绩|宝宝|幼儿|读书|"
                   r"考试|心理|专注|作业|沟通|陪伴|习惯")
BADPATH = re.compile(r"/(sports|auto|money|tech|ent|game|house|travel)/")


ARTICLE_HINT = re.compile(r"/a/\w{8,}|/article/\w{6,}|/news/\w{6,}|/note/\d{5,}|"
                          r"/content/\d{6}/|/\d{7,}\.s?html?|/dy/article/\w{8,}")
SKIP = re.compile(r"/(tag|list|search|login|about|help|topic|author|user|"
                  r"channel|index|video|pic|photo|special)/")


def extract_links(html, base):
    host = urlparse(base).netloc
    out = []
    for m in re.finditer(r'href="([^"#]+)', html):
        u = urljoin(base, m.group(1)).split("?")[0].split("#")[0]
        p = urlparse(u)
        if p.scheme not in ("http", "https"):
            continue
        # 允许主域与 m./c. 子域互认
        h2 = p.netloc.replace("m.", "").replace("c.", "").replace("news.", "").replace("new.", "")
        h1 = host.replace("m.", "").replace("c.", "").replace("news.", "").replace("new.", "")
        if h2 != h1:
            continue
        if SKIP.search(p.path) or not ARTICLE_HINT.search(p.path):
            continue
        out.append(u)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=100)
    ap.add_argument("--per-host", type=int, default=30, help="单个站点最多取几篇")
    ap.add_argument("--delay", type=float, default=0.4, help="每次请求间隔秒")
    ap.add_argument("--max-pages", type=int, default=600, help="最多访问页数（护栏）")
    a = ap.parse_args()

    seen, done = set(), 0
    q = deque(SEEDS)
    results, per_host = [], {}
    t0 = time.time()

    while q and len(results) < a.target and done < a.max_pages:
        u = q.popleft()
        if u in seen:
            continue
        seen.add(u)
        host = urlparse(u).netloc
        if per_host.get(host, 0) >= a.per_host:
            continue
        try:
            html = fetch(u)
        except Exception:  # noqa: BLE001
            continue
        done += 1
        n, seg, title = article_len(html)
        # 加严：标题须含 **≥2 个不同**育儿词（只含 1 个的常是社会新闻/数码/明星蹭词）
        topic_ok = (len(set(TOPIC.findall(title))) >= 2
                    and not BADPATH.search(urlparse(u).path))
        if n >= 400 and topic_ok:         # 像正文 且 主题相关
            results.append((n, host, u))
            per_host[host] = per_host.get(host, 0) + 1
            print(f"[{len(results):>3}] {n:>5} 字  {host:<16} {title[:36]}", flush=True)
        for l in extract_links(html, u):
            if l not in seen:
                q.append(l)
        time.sleep(a.delay)

    print("-" * 96)
    print(f"抓取 {done} 页，得有效样本 {len(results)} 篇，用时 {time.time() - t0:.0f}s")
    if results:
        nums = sorted(x[0] for x in results)
        mid = nums[len(nums) // 2]
        print(f"最短 {nums[0]} ｜ 中位 {mid} ｜ 平均 {sum(nums) // len(nums)} ｜ 最长 {nums[-1]}")
        for lo, hi in ((0, 1000), (1000, 1500), (1500, 2000), (2000, 2500), (2500, 99999)):
            c = sum(1 for x in nums if lo <= x < hi)
            print(f"  {lo:>5}–{hi if hi < 9999 else '∞':>5} 字: {c:>3} 篇 ({c * 100 // len(nums)}%)")


if __name__ == "__main__":
    main()
