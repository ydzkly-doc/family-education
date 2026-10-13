# -*- coding: utf-8 -*-
"""解析中考/高考源词表，提取干净词元（lemma 原形）。
规则只针对这两份文件的实际格式：
- 中考表：单词行形如  `about [...] prep. ...`，音标用 [...] 或（...）包裹
- 高考表：词条分三行 `单词 ` / `[音标]` / `词性. 释义`，单词单独成行
输出每个词表一个 .words.txt（每行一个英文词条）。
"""
import re, os, sys

BASE = os.path.dirname(os.path.abspath(__file__))
VB = os.path.join(BASE, "词表")

PHONETIC = re.compile(r"[/\[［（(].*?[/\]］）)]")
POS = re.compile(r"^(art|n|v|vt|vi|aux|a|ad|adj|adv|prep|pron|conj|num|int|modal|abbr)\b\.?", re.I)
# 一个合法英文词条：字母开头，可含空格/连字符/点
WORDHEAD = re.compile(r"^[A-Za-z][A-Za-z'’.\- ]*")

def clean_head(line):
    s = line.strip().replace("\ufeff", "")
    if not s:
        return None
    # 去掉音标
    s = PHONETIC.sub(" ", s)
    # 取行首英文部分
    m = WORDHEAD.match(s)
    if not m:
        return None
    w = m.group(0).strip(" -.")
    # 处理 a (an) 这类：取第一个
    w = w.split()[0] if w else w
    # 过滤词性缩写误判
    if POS.match(w) and len(w) <= 4:
        return None
    # 只要纯英文/连字符
    if not re.fullmatch(r"[A-Za-z][A-Za-z'’\-]*", w):
        return None
    return w.lower()

def parse_zk(path):
    """中考：单词与音标释义在同一行。"""
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            s = line.strip().replace("\ufeff", "")
            if not s or len(s) <= 2:
                continue
            if PHONETIC.search(s) or POS.search(s):
                w = clean_head(s)
                if w:
                    out.append(w)
            else:
                # 少数无音标行：行首是单词且后面跟中文
                m = re.match(r"^([A-Za-z][A-Za-z'’\-]*)\s+[\u4e00-\u9fff]", s)
                if m:
                    out.append(m.group(1).lower())
    return out

def parse_gk(path):
    """高考：单词单独成行，下一行为 [音标]。
    用“音标行的前一行是单词”这一结构精确提取。"""
    lines = [l.strip().replace("\ufeff", "") for l in open(path, encoding="utf-8")]
    out = []
    for i, s in enumerate(lines):
        if re.fullmatch(r"[/\[［].*?[/\]］]", s) or s.startswith("["):
            # 上一行是单词
            if i - 1 >= 0:
                cand = lines[i-1].strip()
                m = re.match(r"^[A-Za-z][A-Za-z'’\-]*$", cand)
                if m:
                    out.append(cand.lower())
    return out

def main():
    jobs = [
        ("中考英语词汇表_源.txt", "中考_词条.txt", parse_zk),
        ("高考3500_源.txt", "高考3500_词条.txt", parse_gk),
    ]
    for src, dst, fn in jobs:
        p = os.path.join(VB, src)
        words = fn(p)
        uniq = sorted(set(words))
        with open(os.path.join(VB, dst), "w", encoding="utf-8") as f:
            f.write("\n".join(uniq))
        print(f"{src}: 原始命中 {len(words)}，去重后 {len(uniq)} -> {dst}")

if __name__ == "__main__":
    main()
