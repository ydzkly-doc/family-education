# -*- coding: utf-8 -*-
r"""核对某条成片与 `timings.json` 的时间码偏移（成片可能前置过封面卡）。

判据：把 timings 整体平移 offset 后，**末句终点应≈成片时长**（片尾只留一点余量）。
用法：python 工具脚本/video_timecode_offset.py <成片.mp4> <timings.json>
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

FF = os.path.join(os.path.expanduser("~"),
                  ".workbuddy", "binaries", "ffmpeg", "bin", "ffmpeg.exe")


def duration(p: str) -> float:
    r = subprocess.run([FF, "-hide_banner", "-i", os.path.abspath(p)],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    m = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", r.stderr or "")
    if not m:
        raise SystemExit(f"⛔ 读不到时长：{p}\n{(r.stderr or '')[-300:]}")
    h, mi, s = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(s)


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    mp4, tj = sys.argv[1], sys.argv[2]
    D = duration(mp4)
    d = json.load(open(tj, encoding="utf-8"))
    L = d["lines"] if isinstance(d, dict) else d
    first, last = float(L[0]["start"]), float(L[-1]["end"])
    tail = D - last
    print(f"成片      : {os.path.basename(mp4)}  时长 {D:.2f}s")
    print(f"timings   : {len(L)} 行  首句起 {first:.2f}s  末句终 {last:.2f}s")
    print(f"片尾余量（未平移）: {tail:.2f}s")
    # 成片若无前置，末句终点≈时长；否则差多少就是 offset
    guess = round(tail, 1)
    print(f"→ 推定 offset ≈ {guess:+.1f}s"
          + ("（与 2.0s 封面卡一致）" if abs(guess - 2.0) < 0.35 else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
