# -*- coding: utf-8 -*-
"""系列正文字数/篇幅统计（剥 HTML，只算正文汉字数与总字符数）。

用途：给「视频号口播覆盖八成」做篇幅判断——先知道原文多长，再定视频时长。
用法：
    python series_word_count.py "<系列目录>"            # 递归找 正文_*.html，逐篇统计
    python series_word_count.py "<系列目录>" --md       # 同时统计同名 md
输出：每篇一行（文件名 / 汉字数 / 总字数 / 按 ÷4.3 的口播时长参考）。
说明：汉字数 = 中文汉字个数；总字数 = 汉字+字母+数字（不含标点与空白），
      与公众号「正文字数」口径接近。附录（工具卡/来源声明）未单独剥离。
"""
import argparse
import glob
import os
import re
import sys

TAG_RE = re.compile(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>|<[^>]+>", re.I)
HAN_RE = re.compile(r"[\u4e00-\u9fff]")
WORD_RE = re.compile(r"[\u4e00-\u9fffa-zA-Z0-9]")


def clean(html: str) -> str:
    txt = TAG_RE.sub("\n", html)
    txt = txt.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return txt


def stat_file(path: str):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        raw = f.read()
    txt = clean(raw) if path.lower().endswith((".html", ".htm")) else raw
    han = len(HAN_RE.findall(txt))
    words = len(WORD_RE.findall(txt))
    return han, words


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", help="系列目录")
    ap.add_argument("--md", action="store_true", help="同时统计 md 正文")
    args = ap.parse_args()

    pats = ["**/正文_*.html"] + (["**/*.md"] if args.md else [])
    files = []
    for p in pats:
        files += glob.glob(os.path.join(args.root, p), recursive=True)
    files = sorted(set(files))
    if not files:
        print("未找到匹配文件")
        return
    print(f"{'文件':<58}{'汉字':>7}{'总字数':>8}{'口播时长(÷4.3)':>16}")
    print("-" * 95)
    for f in files:
        han, words = stat_file(f)
        rel = os.path.relpath(f, args.root)
        if len(rel) > 56:
            rel = "…" + rel[-55:]
        sec = words / 4.3
        print(f"{rel:<58}{han:>7}{words:>8}{sec/60:>10.1f} 分{sec % 60:>4.0f} 秒")
    print("-" * 95)
    print("提示：视频目标＝覆盖原文约八成 → 口播字数 ≈ 总字数 × 0.8（另加开场/收尾的少量自撰句）。")


if __name__ == "__main__":
    main()
