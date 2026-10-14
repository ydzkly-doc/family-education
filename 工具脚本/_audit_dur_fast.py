# -*- coding: utf-8 -*-
"""快速体检：只对比 容器/视频/音频 时长差（不做静音解码）。"""
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _probe_tail_silence import probe  # noqa: E402

ROOT = sys.argv[1] if len(sys.argv) > 1 else r"公众号/改善你的亲子关系/视频号文案"
files = sorted(glob.glob(os.path.join(ROOT, "[01][0-9]_*", "_成品", "成片_[01][0-9].mp4")))
print(f"共 {len(files)} 条\n")
bad = []
for f in files:
    info = probe(f)
    fmt = float(info["format"]["duration"])
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), {})
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    vd = float(v.get("duration", 0))
    ad = float(a.get("duration", 0)) if a else 0
    diff = fmt - ad
    name = os.path.basename(os.path.dirname(os.path.dirname(f)))
    flag = "  ❌" if diff > 0.35 else ""
    if diff > 0.35:
        bad.append((f, diff))
    print(f"{name[:24]:26s} 容器{fmt:7.2f} 视频{vd:7.2f} 音频{ad:7.2f} 差{diff:6.2f}{flag}")
print("\n问题条：", len(bad))
for f, d in bad:
    print("  ", f, f"{d:.2f}s")
