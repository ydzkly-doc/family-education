# -*- coding: utf-8 -*-
'''口播通顺性体检（2026-10-03 用户点名后新增）。

针对的问题（用户原话：「这是口播文案，通顺、语义表达准确是最重要的」）：
  ① 悬空行    —— 口播区某行以「，、；：」结尾，提词器会把人名与台词断在两行；
  ② 引号      —— 口播区/提词器区混入中文引号，或 ASCII 引号不成对（出镜者看稿会误读）；
  ③ 咬合      —— 本条承上句与上一条过渡句没有逐字回扣（改了上一条忘了下一条）；
  ④ 短句串    —— 一段里连续 ≥3 行都是短句（对话/清单），提示人工核「这句是谁说的」。

用法：video_script_flow_check.py <系列目录>
退出码：有 FAIL 则 1。
'''
import glob
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

P_END = "。？！"          # 合法的行尾
P_SUSPEND = "，、；：,;:"   # 悬空行尾
CJK_Q = "\u201c\u201d"
SHORT = 9                 # 「短句」的字数阈值（用于提示人工核引语归属）


def oral_block(t):
    if "## 一、口播文案" not in t:
        return ""
    return t.split("## 一、口播文案", 1)[1].split("\n## ", 1)[0]


def prompt_block(t):
    if "## 二、提词器文案" not in t:
        return ""
    return t.split("## 二、提词器文案", 1)[1].split("\n## ", 1)[0]


def clean(s):
    return re.sub(r"[\s，。、；：？！,;:\.\?\!\"'\u201c\u201d\u300c\u300d\u2014\u2018\u2019()（）]", "", s)


def after(lines, marker, maxlines=2):
    """取标记之后最多 maxlines 行（过渡句常写成两行，只取一行会漏判咬合）。"""
    for i, l in enumerate(lines):
        if l.strip().startswith(marker):
            out = []
            rest = l.strip()[len(marker):].strip()
            if rest:
                out.append(rest)
            for j in range(i + 1, min(i + 6, len(lines))):
                s = lines[j].strip()
                if s:
                    out.append(s)
                    if len(out) >= maxlines:
                        break
            return " ".join(out)
    return ""


def main():
    if len(sys.argv) < 2:
        raise SystemExit("用法：video_script_flow_check.py <系列目录>")
    root = sys.argv[1]
    dirs = sorted(d for d in os.listdir(root)
                  if os.path.isdir(os.path.join(root, d)) and not d.startswith("_"))
    items = []
    for d in dirs:
        fs = glob.glob(os.path.join(root, d, "视频号文案_*.md"))
        if fs:
            items.append((d, io.open(fs[0], encoding="utf-8").read()))

    bad = 0
    print(f"=== 口播通顺性体检（{len(items)} 条）===")

    for name, t in items:
        seq = re.search(r"发布第(\d+)条", name)
        tag = f"{seq.group(1) if seq else '??'} {name[:14]}"
        probs = []
        hints = []

        # ① 悬空行
        for i, ln in enumerate(oral_block(t).split("\n"), 1):
            s = ln.strip()
            if not s or s.startswith("#") or s.startswith("【"):
                continue
            if s[-1] in P_SUSPEND:
                probs.append(f"悬空行（以「{s[-1]}」结尾）：{s[:26]}")

        # ② 引号
        for label, blk in (("口播区", oral_block(t)), ("提词器区", prompt_block(t))):
            body = "\n".join(l for l in blk.split("\n") if not l.strip().startswith(">"))
            if any(c in body for c in CJK_Q):
                probs.append(f"{label}混入中文引号（应统一 ASCII 双引号）")
            if body.count('"') % 2:
                probs.append(f"{label} ASCII 双引号不成对（{body.count(chr(34))} 个）")

        # ③ 短句串 —— 只是「提示」：短句连排不等于错，是要人眼核一句「这句是谁说的」
        run, in_run = 0, []
        for ln in oral_block(t).split("\n"):
            s = ln.strip()
            if not s or s.startswith("【"):
                continue
            if len(clean(s)) <= SHORT:
                run += 1
                in_run.append(s)
            else:
                if run >= 3:
                    hints.append(f"连续 {run} 行短句，核「这句是谁说的」：{' ／ '.join(in_run[:3])}…")
                run, in_run = 0, []
        if run >= 3:
            hints.append(f"连续 {run} 行短句，核「这句是谁说的」：{' ／ '.join(in_run[:3])}…")

        if probs:
            bad += 1
            print(f"\n⚠️ {tag}")
            for p in probs:
                print(f"   · {p}")
        if hints:
            print(f"\n💡 {tag}")
            for h in hints:
                print(f"   · {h}")

    # ④ 咬合（跨条）
    print("\n=== 承上启下咬合 ===")
    for idx in range(1, len(items)):
        pname, pt = items[idx - 1]
        name, t = items[idx]
        up = after(oral_block(t).split("\n"), "【开场·接上一条】")
        down = after(oral_block(pt).split("\n"), "【合集·过渡】")
        # ⚠️ 承上首句的句末标点**可能是 ？**（问句式的承上，2026-10-05 起多了）
        #    —— 只按「。」切会把后面两句一起吃进来，咬合永远判不过（工具 bug，已修）
        #    ⚠️ 正则必须带**捕获组**，否则切出来的不是标点、而是「标点之后的所有内容」
        _m = re.split(r"([。？！])", up, maxsplit=1)
        up_first = _m[0] + (_m[1] if len(_m) > 1 else "。")
        core = clean(re.sub(r"^上一条(我)?说[，,]?", "", up_first))
        if not core or not down:
            continue
        if core in clean(down):
            print(f"  ✅ {idx + 1:02d} ← {idx:02d}：逐字咬合（{core[:20]}…）")
        else:
            bad += 1
            print(f"  ❌ {idx + 1:02d} ← {idx:02d}：接不上")
            print(f"      本条承上：{up}")
            print(f"      上条过渡：{down}")

    print(f"\n{'❌ 有需人工核的地方' if bad else '✅ 全部通过'}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
