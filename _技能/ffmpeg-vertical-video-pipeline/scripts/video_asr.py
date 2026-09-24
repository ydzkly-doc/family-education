# -*- coding: utf-8 -*-
r"""
语音识别 + 文案对齐 —— 拿到"第几秒说哪一句"

本项目的特殊之处：**文案已知**（MD 里给的【照着念】），
所以比"纯 ASR 听写"简单——我们只需要**时间码**，文字用已知的那份。

做法：
  ① faster-whisper 转写，取 **词级时间戳**（word_timestamps=True）
  ② 把「已知文案」与「ASR 输出」各自规范化（去标点空格），
     用 difflib.SequenceMatcher 做**全局序列对齐**（不是逐句匹配，更稳）
  ③ 按对齐结果，把每一行文案映射到 ASR 词的时间区间
  ④ 匹配不上的行，用前后相邻行插值兜底（保证不漏行）

用法：
  python video_asr.py --video <视频> --script <文案txt> --out <timings.json>
  python video_asr.py --video <视频> --selftest-align    # 只测对齐逻辑，不跑模型

文案 txt 格式：一行一句（空行与 # 开头的行会被忽略）
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import paths  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# 与文案无关的字符：标点、空白、符号
KEEP = re.compile(r"[^\u4e00-\u9fff\u3400-\u4dbf0-9A-Za-z]")


def norm(s: str) -> str:
    """规范化：只留中日韩汉字、数字、字母"""
    return KEEP.sub("", s)


def load_script(path: str) -> list[str]:
    lines = []
    with open(path, encoding="utf-8-sig") as f:
        for raw in f:
            t = raw.strip()
            if not t or t.startswith("#"):
                continue
            lines.append(t)
    return lines


# ---------------- 对照表：规范化字符串的每个字符在原结构中的下标 ----------------
def build_index(texts: list[str]) -> tuple[str, list[int]]:
    """texts = [行1, 行2, ...] -> (规范化拼接串, 每字符所属行号)"""
    buf, owner = [], []
    for i, t in enumerate(texts):
        for ch in norm(t):
            buf.append(ch)
            owner.append(i)
    return "".join(buf), owner


def build_word_index(words: list[dict]) -> tuple[str, list[int]]:
    """words = [{"word":..., "start":..., "end":...}] -> (规范化串, 每字符所属词号)"""
    buf, owner = [], []
    for i, w in enumerate(words):
        for ch in norm(w.get("word", "")):
            buf.append(ch)
            owner.append(i)
    return "".join(buf), owner


def align_lines_to_words(lines: list[str], words: list[dict]) -> list[dict]:
    """
    返回 [{"text":行文本, "start":秒, "end":秒, "matched":bool}, ...]
    """
    if not words or not lines:
        return [{"text": t, "start": 0.0, "end": 0.0, "matched": False} for t in lines]

    a, a_owner = build_index(lines)
    b, b_owner = build_word_index(words)

    # a / b 中每个字符 -> 对应的词区间
    line_span: dict[int, list[int]] = {}     # 行 -> [词下标...]
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            ai, bi = blk.a + k, blk.b + k
            ln = a_owner[ai]
            wi = b_owner[bi]
            line_span.setdefault(ln, []).append(wi)

    out = []
    for i, t in enumerate(lines):
        ws = line_span.get(i)
        if ws:
            lo, hi = min(ws), max(ws)
            out.append({
                "text": t,
                "start": round(float(words[lo]["start"]), 3),
                "end": round(float(words[hi]["end"]), 3),
                "matched": True,
            })
        else:
            out.append({"text": t, "start": None, "end": None, "matched": False})

    # 未匹配的行用前后插值兜底
    for i, item in enumerate(out):
        if item["matched"]:
            continue
        prev = next((out[j] for j in range(i - 1, -1, -1) if out[j]["matched"]), None)
        nxt = next((out[j] for j in range(i + 1, len(out)) if out[j]["matched"]), None)
        if prev and nxt:
            item["start"] = round(prev["end"], 3)
            item["end"] = round(nxt["start"], 3)
        elif prev:
            item["start"] = round(prev["end"], 3)
            item["end"] = round(prev["end"] + 1.5, 3)
        elif nxt:
            item["start"] = round(max(0.0, nxt["start"] - 1.5), 3)
            item["end"] = round(nxt["start"], 3)
        else:
            item["start"], item["end"] = 0.0, 1.0

    # 修一遍时间单调性（字幕不能倒退或重叠）
    prev_end = 0.0
    for item in out:
        if item["start"] < prev_end:
            item["start"] = round(prev_end, 3)
        if item["end"] <= item["start"]:
            item["end"] = round(item["start"] + 0.6, 3)
        prev_end = item["end"]
    return out


# ---------------- ASR ----------------
def transcribe_segments(video: str, model_size: str = "small", language: str = "zh",
                        device: str = "cpu", compute_type: str = "int8") -> list[dict]:
    """
    不依赖已知文案，直接把 ASR 的分段当作字幕行。
    用途：① 素材没有配套文案时 ② 纯听写场景 ③ 管道冒烟测试
    """
    from faster_whisper import WhisperModel
    print(f"  载入模型 {model_size}")
    model = WhisperModel(paths.resolve_whisper(model_size), device=device,
                         compute_type=compute_type)
    print(f"  转写中：{video}")
    segments, info = model.transcribe(
        video, language=language, word_timestamps=False, vad_filter=True,
        initial_prompt="以下是普通话口播，内容关于家庭教育、亲子沟通。",
    )
    out = []
    for seg in segments:
        t = seg.text.strip()
        if t:
            out.append({"text": t, "start": round(seg.start, 3),
                        "end": round(seg.end, 3), "matched": True})
            print(f"    [{seg.start:7.2f}-{seg.end:7.2f}] {t}")
    return out


def transcribe(video: str, model_size: str = "small", language: str = "zh",
               device: str = "cpu", compute_type: str = "int8") -> list[dict]:
    from faster_whisper import WhisperModel
    print(f"  载入模型 {model_size}（首次会自动下载…）")
    model = WhisperModel(paths.resolve_whisper(model_size), device=device,
                         compute_type=compute_type)
    print(f"  转写中：{video}")
    segments, info = model.transcribe(
        video, language=language, word_timestamps=True, vad_filter=True,
        initial_prompt="以下是普通话口播，内容关于家庭教育、亲子沟通。",
    )
    words = []
    for seg in segments:
        for w in (seg.words or []):
            words.append({"word": w.word, "start": w.start, "end": w.end})
        print(f"    [{seg.start:7.2f}-{seg.end:7.2f}] {seg.text.strip()}")
    print(f"  共 {len(words)} 个词/字")
    return words


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video")
    ap.add_argument("--script")
    ap.add_argument("--out")
    ap.add_argument("--model", default="small")
    ap.add_argument("--lang", default="zh")
    ap.add_argument("--selftest-align", action="store_true")
    args = ap.parse_args()

    if args.selftest_align:
        # 用一段"故意有错字、有漏字"的 ASR 输出来验证对齐的鲁棒性
        lines = ["那阵子我儿子老喊肚子疼。", "有时候是头疼。", "是孩子他妈带他去的医院。",
                 "我没去。", "查了几次，也没查出什么毛病来。"]
        words = []
        t = 0.3
        for txt, dur in [("那阵子", .8), ("我儿子", .7), ("老喊", .5), ("肚子疼", .8),
                         ("有时候", .7), ("是头疼", .8),
                         ("是孩子", .7), ("他妈", .5), ("带他去的", .9), ("医院", .6),
                         ("我", .3), ("没去", .6),
                         ("查了", .5), ("几次", .5), ("也", .3), ("没查出", .7),
                         ("什么", .4), ("毛病来", .7)]:
            words.append({"word": txt, "start": round(t, 3), "end": round(t + dur, 3)})
            t += dur + 0.15
        res = align_lines_to_words(lines, words)
        print("=" * 72)
        print("对齐自检（文案 5 行 vs ASR 18 个词）")
        print("=" * 72)
        for r in res:
            print(f"  {'✓' if r['matched'] else '·'} [{r['start']:7.2f} - {r['end']:7.2f}]  {r['text']}")
        ok = all(r["matched"] for r in res)
        print(f"\n  全部行均匹配：{'是 ✅' if ok else '否'}")
        return

    if not (args.video and args.script and args.out):
        ap.error("需要 --video --script --out，或使用 --selftest-align")

    lines = load_script(args.script)
    print(f"文案 {len(lines)} 行：{args.script}")
    words = transcribe(args.video, args.model, args.lang)
    res = align_lines_to_words(lines, words)

    payload = {
        "video": os.path.abspath(args.video),
        "model": args.model,
        "lines": res,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    print(f"\n已写出时间码：{args.out}")
    for r in res:
        flag = "✓" if r["matched"] else "·"
        print(f"  {flag} [{r['start']:7.2f} - {r['end']:7.2f}]  {r['text']}")


if __name__ == "__main__":
    main()
