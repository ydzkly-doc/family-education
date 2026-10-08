# -*- coding: utf-8 -*-
"""把口播区＋提词器区里的中文弯引号统一为 ASCII 双引号（系列既定口径）。
其他区块不动。--apply 写盘。"""
import io, os, re, sys, glob
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, "公众号", "手机方案", "视频号文案")
APPLY = "--apply" in sys.argv

def section(t, key, nextkeys):
    m = re.search(r"^## [^\n]*" + key + r"[^\n]*$", t, re.M)
    if not m:
        return None, t
    start = m.end()
    nxt = re.search(r"^## ", t[start:], re.M)
    end = start + nxt.start() if nxt else len(t)
    return t[start:end], (t[:start], t[end:])

total = 0
for f in glob.glob(os.path.join(BASE, "*", "视频号文案_*.md")):
    t = io.open(f, encoding="utf-8").read()
    changed = False
    for key in ("口播文案", "提词器文案"):
        seg, bounds = section(t, key, ())
        if seg is None:
            continue
        if "\u201c" in seg or "\u201d" in seg:
            n = seg.count("\u201c") + seg.count("\u201d")
            newseg = seg.replace("\u201c", '"').replace("\u201d", '"')
            pre, post = bounds
            t = pre + newseg + post
            total += n
            changed = True
    if changed and APPLY:
        io.open(f, "w", encoding="utf-8").write(t)
    if changed:
        print("✅ %s" % os.path.basename(os.path.dirname(f)))
print("\n共替换 %d 个引号  %s" % (total, "已写盘" if APPLY else "DRY-RUN"))
