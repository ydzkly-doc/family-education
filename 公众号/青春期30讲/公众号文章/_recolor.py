# -*- coding: utf-8 -*-
"""青春期30讲 正文配色：按三季替换暖橘色为莫兰迪季色。
只替换橘/暖强调色系，正文黑灰、米白背景保留。
季：1-5 暖陶橘 / 6-12 雾蓝绿 / 13-18 暖金棕。
用法: python recolor.py <起始篇> <结束篇>   （含端点）；不传则处理全部 1-18。
"""
import os, re, sys, glob

BASE = r"D:\个人资料\家庭教育\青春期30讲\公众号文章"

# 旧橘色系 -> 各季新色系。键为旧色(小写)，值为 dict: {季: 新色}
# 三季色板
SEASONS = {
    "orange": {  # 一季 搞关系：暖陶橘（比原橘略灰一点、莫兰迪化）
        "main":  "#c0764f",   # 原 #c8643c
        "deep":  "#a55f3e",   # 原 #b0552f
        "light": "#e3cdbb",   # 原 #e0c9b4 浅米橘底
        "band":  "#f0dccb",   # 原 #ecd9c8
        "peach": "#f6dcc8",   # 原 #f6d9c2
        "f0a8":  "#e8b483",   # 原 #f0a868 亮橙点缀
        "e08a":  "#cf9066",   # 原 #e08a5f
        "ffe9":  "#fbe6d4",   # 原 #ffe9d6
    },
    "teal": {    # 二季 做功课：莫兰迪雾蓝绿
        "main":  "#5f8a86",
        "deep":  "#4a6f6c",
        "light": "#c4d6d3",
        "band":  "#d3e2df",
        "peach": "#d8e6e3",
        "f0a8":  "#8fb5b1",
        "e08a":  "#7aa5a1",
        "ffe9":  "#e6efed",
    },
    "gold": {    # 三季 给信心：莫兰迪暖金棕
        "main":  "#c0924f",
        "deep":  "#a47a3a",
        "light": "#e2d2b4",
        "band":  "#ecdfc6",
        "peach": "#f0e2c6",
        "f0a8":  "#d9b877",
        "e08a":  "#cf9f5f",
        "ffe9":  "#f6ecd6",
    },
}

# 旧色 -> 色板键位
OLD_MAP = {
    "#c8643c": "main",
    "#b0552f": "deep",
    "#e0c9b4": "light",
    "#ecd9c8": "band",
    "#f6d9c2": "peach",
    "#f0a868": "f0a8",
    "#e08a5f": "e08a",
    "#ffe9d6": "ffe9",
}

def season_of(num):
    if num <= 5:  return "orange"
    if num <= 12: return "teal"
    return "gold"

def recolor_file(path, num, dry=False):
    with open(path, "r", encoding="utf-8") as f:
        txt = f.read()
    pal = SEASONS[season_of(num)]
    def repl(m):
        old = m.group(0).lower()
        key = OLD_MAP.get(old)
        if not key:  # 非橘色系（黑灰/米白/绿点缀等）保留
            return m.group(0)
        return pal[key]
    new = re.sub(r"#[0-9a-fA-F]{6}", repl, txt)
    if new != txt and not dry:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new)
    return new != txt

def main():
    lo = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    hi = int(sys.argv[2]) if len(sys.argv) > 2 else 18
    for folder in sorted(os.listdir(BASE)):
        p = os.path.join(BASE, folder)
        if not (os.path.isdir(p) and folder.startswith("发布包_")): continue
        m = re.search(r"第(\d+)篇", folder)
        if not m: continue
        num = int(m.group(1))
        if not (lo <= num <= hi): continue
        files = glob.glob(os.path.join(p, "正文_第%d篇_*.html" % num))
        files = [x for x in files if "备份" not in x]
        for fp in files:
            changed = recolor_file(fp, num)
            print(("  [改] " if changed else "  [--] ") + "%s 季=%s" % (os.path.basename(fp), season_of(num)))

if __name__ == "__main__":
    main()
