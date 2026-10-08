# -*- coding: utf-8 -*-
"""对手机方案34条批量跑硬指标/标点/锚点/折行，出总表。"""
import io, os, re, sys, glob, subprocess
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, "公众号", "手机方案", "视频号文案")
PY = sys.executable
checks = {
 "硬指标": "video_script_check.py",
 "标点": "video_script_punct_check.py",
 "锚点": "video_script_anchor_check.py",
 "折行": "video_script_wrap_check.py",
}
files = sorted(glob.glob(os.path.join(BASE, "*", "视频号文案_*.md")))
summary = {k: [0, []] for k in checks}
detail_bad = []
for f in files:
    name = os.path.basename(os.path.dirname(f))
    for k, script in checks.items():
        p = subprocess.run([PY, os.path.join(ROOT, "工具脚本", script), f],
                           capture_output=True, text=True, encoding="utf-8")
        out = (p.stdout + p.stderr)
        ok = ("❌" not in out) and p.returncode == 0
        if ok:
            summary[k][0] += 1
        else:
            summary[k][1].append(name)
            if k == "硬指标":
                # 抓失败行
                for ln in out.split("\n"):
                    if "❌" in ln:
                        detail_bad.append((name, ln.strip()))

print("共 %d 条\n" % len(files))
for k, (n, bad) in summary.items():
    print("%s：通过 %d/%d  %s" % (k, n, len(files), ("失败: " + ",".join(bad)) if bad else ""))
if detail_bad:
    print("\n硬指标失败明细：")
    for name, ln in detail_bad:
        print("  [%s] %s" % (name, ln[:70]))
