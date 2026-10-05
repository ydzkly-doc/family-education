# -*- coding: utf-8 -*-
"""上屏句「折行」体检（只读）——把 SOP 3.18 ①′（hk55，2026-10-03 立）落成工具。

为什么要有它（2026-10-03）：
    折行判据是「**第一个分句的视觉字数落在 `[总长 − 10, 10]`**」，人眼算不了；
    而"标点开头的第二行""词被劈开"这两样**只看落点表发现不了**，
    旧流程要跑到 `--preview` 生成 `preview.ass` 才能看出来——**写稿阶段就该拦住**。
    → 本脚本直接调用管道自己的 `wrap_cjk()`（唯一真相源，不复制算法）。

它报三件事：
    ① **行数**（强调 82px / 金句钩子 100px）
    ② **第二行是不是以标点开头**（❌ 逗号被甩到行首）
    ③ **第一分句是否落在判据区间内**（不在 → 断点会跑到词中间）

用法：
    PY="C:/Users/ZhuanZ/.workbuddy/binaries/python/versions/3.13.12/python.exe"
    "$PY" 工具脚本/video_script_wrap_check.py "<文案.md>"

退出码：0 = 全部通过；1 = 有 FAIL。
"""
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

SKILL_SCRIPTS = os.path.join(
    os.path.expanduser("~"), ".workbuddy", "skills",
    "ffmpeg-vertical-video-pipeline", "scripts")
sys.path.insert(0, SKILL_SCRIPTS)
from video_build_ass import wrap_cjk, text_width  # noqa: E402

MAX_W = 860.0          # 可用宽（px）
CLAUSE_SPLIT = re.compile(r"[，、；：]")
PUNCT_HEAD = set("，。、；：！？）】》」’”")


def first_clause(s: str) -> int:
    """第一个分句的视觉字数（含标点；没有分句标点则返回整句长度）。"""
    m = CLAUSE_SPLIT.search(s)
    return len(s[:m.end()]) if m else len(s)


def check(label: str, text: str, fontsize: float, cap: int, maxlines: int = 2):
    """cap ＝ 一行大约放得下的字数（82px→10、100px→9、76px→11）。"""
    total = len(re.sub(r"\s", "", text))
    lines = wrap_cjk(text, fontsize, MAX_W).split("\n")
    fails = []
    if len(lines) > maxlines:
        fails.append(f"{len(lines)} 行 > {maxlines} 行（会顶到脸）")
    for i, ln in enumerate(lines):
        if ln[:1] in PUNCT_HEAD:
            fails.append(f"第 {i + 1} 行以标点开头（{ln[:6]}…）")
    fc = first_clause(text)
    lo, hi = max(total - cap, 1), cap
    ok_zone = lo <= fc <= hi
    # ⚠️ 判据只在**折成 2 行**时有意义：3 行以上时"总长 − cap"已经 > cap，区间本身不成立
    #    （浅底卡允许 3 行，见 SOP 3.18① 的表）。所以 3 行及以上只查"标点开头"。
    if len(lines) == 2 and not ok_zone:
        fails.append(f"第一个分句 {fc} 字不在 [{lo}, {hi}] → 断点会落在词中间")
    flag = "✅" if not fails else "❌"
    print(f"  {flag} [{label}] {total} 字 {len(lines)} 行｜首分句 {fc} 字")
    for ln in lines:
        print(f"        ｜{ln}")
    if len(lines) == 2 and not ok_zone:
        print(f"        💡 删可省词（所以／并且／其实／后来）或缩短第一个分句，"
              f"到 {hi} 字以内")
    return fails


def main():
    if "--probe" in sys.argv:
        i = sys.argv.index("--probe")
        text = sys.argv[i + 1]
        px = float(sys.argv[i + 2]) if len(sys.argv) > i + 2 else 82.0
        cap = {82.0: 10, 100.0: 9, 76.0: 11}.get(px, 10)
        ml = 3 if px == 76.0 else 2
        print(f"=== 试算：{px:.0f}px（cap {cap} 字／行，最多 {ml} 行）===")
        check(f"probe {px:.0f}px", text, px, cap, ml)
        return 0

    if len(sys.argv) < 2:
        raise SystemExit("用法：video_script_wrap_check.py <文案.md>\n"
                         "      或：video_script_wrap_check.py --probe \"某句话\" 82")
    path = sys.argv[1]
    t = io.open(path, encoding="utf-8").read()

    # 取「上屏方案」区块（编号任意；结束认下一个 ## 或 # 【）
    m = re.search(r"^#{2,4}[^\n]*上屏方案[^\n]*\n(.*?)(?=\n#{1,2}\s|\Z)", t, re.S | re.M)
    if not m:
        raise SystemExit("❌ 找不到含「上屏方案」的节标题")
    blk = m.group(1)

    cur = ""
    jobs = []          # (区块名, 句子, fontsize, cap, maxlines)
    LIM = {"开头钩子": (100, 9, 2), "强调句": (82, 10, 2), "金句大字卡": (100, 9, 2),
           "序号条": (82, 10, 2), "浅底卡": (76, 11, 3), "封面": (100, 9, 2)}
    for line in blk.split("\n"):
        s = line.strip()
        if s.startswith("###"):
            cur = ""
            for k in LIM:
                if k in s:
                    cur = k
                    break
            continue
        if not cur or cur not in LIM:
            continue
        if s.startswith(">") or not s:
            continue
        # ⚠️ **「挂句」不是上屏文字**（2026-10-03 实测踩到）：
        #   挂句只决定卡片**什么时候出现**，它的字数与折行无关；
        #   把它一起算会报出一堆假 FAIL（例：浅底卡的挂句 25 字 → 误报"3 行"）。
        #   → 取法同 `video_script_check.py`：含"挂在"时**只认"挂在"之前**的卡面。
        if "挂句" in s and "挂在" not in s:
            continue
        if "挂在" in s:
            s = s.split("挂在", 1)[0]
        texts = re.findall(r"\*\*([^*]+)\*\*", s) if cur in ("开头钩子", "封面") else []
        texts += re.findall(r"「([^」]+)」", s)
        for x in texts:
            x = x.strip()
            if not x or "秒" in x or "＝" in x:
                continue
            if cur in ("开头钩子", "封面") and len(texts) > 1 and x != texts[0]:
                continue          # 备选不检
            jobs.append((cur, x, *LIM[cur]))

    if not jobs:
        print("没解析到上屏句")
        return 1

    print(f"=== 折行体检：{os.path.basename(path)}（可用宽 {MAX_W:.0f}px）===")
    bad = 0
    for label, text, fs, cap, ml in jobs:
        if check(f"{label} {int(fs)}px", text, fs, cap, ml):
            bad = 1
    print()
    print("✅ 折行全部通过" if not bad else "❌ 有句子需要改（见上）")
    return bad


if __name__ == "__main__":
    sys.exit(main())
