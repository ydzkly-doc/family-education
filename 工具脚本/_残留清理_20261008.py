# -*- coding: utf-8 -*-
"""清理系列方案/发布方案说明区残留的“上一条我说了…”开头。--apply 写盘。"""
import io, os, re, sys, glob
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, "公众号", "手机方案", "视频号文案")
APPLY = "--apply" in sys.argv

pat = re.compile(r"> 上一条我说了[「\"“][^」\"”]+[」\"”]，这一条")
total = 0
for f in glob.glob(os.path.join(BASE, "*", "视频号文案_*.md")):
    t = io.open(f, encoding="utf-8").read()
    n = len(pat.findall(t))
    if n:
        t = pat.sub("> 这一条", t)
        if APPLY:
            io.open(f, "w", encoding="utf-8").write(t)
        total += n
        print("✅ %s 清 %d" % (os.path.basename(os.path.dirname(f)), n))
print("\n共 %d 处  %s" % (total, "已写盘" if APPLY else "DRY-RUN"))
