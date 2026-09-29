# -*- coding: utf-8 -*-
r"""
标色完整性检查 —— 抓"标色词静默丢失"。

背景（2026-09-27）：
    管道的 `render_line()` 是**在折行之后**找标色词的；一旦标色词正好**跨行**
    （折行处插了 `\N`），`find()` 就会失败，而它按"匹配不到就忽略"处理 →
    **那一句一点颜色都没有，而且落点表、预览表都看不出来**（只能逐行读 `.ass`）。
    已在技能侧修好（改为"扁平化后定位、映射回原索引"），本脚本用于**回归核对**：
    保证 MD 里写了几处标色，`.ass` 里就真有那几处 `{\c...}`。

用法：
    PY="C:/Users/ZhuanZ/.workbuddy/binaries/python/envs/default/Scripts/python.exe"

    # 1) 先出预览（不需要素材，几秒）
    cd C:/Users/ZhuanZ/.workbuddy/skills/ffmpeg-vertical-video-pipeline
    "$PY" scripts/video_make.py --md "…/视频号文案_0N_….md" --preview

    # 2) 再核对（自动找同目录的 preview.ass / _成品/_过程文件/subs.ass）
    "$PY" 工具脚本/check_mark_color.py "…/视频号文案_0N_….md"

退出码：0 = 全部着色；1 = 有标色词没上色。
"""
from __future__ import annotations

import io
import os
import re
import sys

# 「卡面/上屏文字」 → 标色词标暖色
ITEM_RX = re.compile(r"「(.+?)」.*?([“\"][^”\"]+[”\"])\s*标")
TAG_RX = re.compile(r"\{[^}]*\}")
PUNCT_RX = re.compile(r"[，。？！、：；·—－\-…“”\"'（）()《》\s]")


def norm(s: str) -> str:
    """去 ASS 行内标签 / 折行符 / 标点，便于跨来源比对"""
    s = TAG_RX.sub("", s).replace("\\N", "").replace("\\n", "")
    return PUNCT_RX.sub("", s)


def parse_md(md_path: str):
    """抽出 MD 里所有『「文本」→ "标色词"标…』的条目"""
    t = io.open(md_path, encoding="utf-8").read()
    out = []
    for ln in t.splitlines():
        ln = ln.strip()
        if not ln.startswith(("-", "1", "2", "3", "4", "5", "6", "7", "8", "9")):
            continue
        m = ITEM_RX.search(ln)
        if not m:
            continue
        text, word = m.group(1), m.group(2)[1:-1]
        if text.startswith("**") or word.startswith("*"):
            continue                      # 模板占位行
        out.append((text, word))
    return out


def find_ass(md_path: str):
    """优先用出片后的 subs.ass（真值），退回 preview.ass"""
    d = os.path.dirname(os.path.abspath(md_path))
    cands = [
        os.path.join(d, "_成品", "_过程文件", "subs.ass"),
        os.path.join(d, "_过程文件", "preview.ass"),
        os.path.join(d, "_成品", "_过程文件", "preview.ass"),
    ]
    for p in cands:
        if os.path.exists(p):
            return p
    return None


def main(argv):
    mds = [a for a in argv if a.lower().endswith(".md")]
    if not mds:
        root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
        vdir = os.path.join(root, "公众号", "孩子不上学了怎么办", "视频号文案")
        if os.path.isdir(vdir):
            for sub in sorted(os.listdir(vdir)):
                p = os.path.join(vdir, sub)
                if os.path.isdir(p):
                    mds += [os.path.join(p, f) for f in sorted(os.listdir(p))
                            if f.endswith(".md") and f.startswith("视频号文案")]
    if not mds:
        print("用法：python check_mark_color.py <文案.md> [更多 md…]")
        return 1

    bad_total = 0
    for md in mds:
        items = parse_md(md)
        ass = find_ass(md)
        name = os.path.basename(os.path.dirname(md))
        print("=" * 66)
        print(f"{name}   （标色条目 {len(items)}）")
        if not ass:
            print("  ⚠️ 找不到 .ass —— 先跑 `--preview` 再核对")
            continue
        print(f"  数据源：{os.path.relpath(ass)}")
        text = io.open(ass, encoding="utf-8-sig", errors="replace").read()
        rows = []
        for ln in text.splitlines():
            if ln.startswith("Dialogue:"):
                parts = ln.split(",", 9)
                if len(parts) == 10:
                    rows.append((parts[3], parts[9]))       # (样式, 正文)

        miss, ok = [], 0
        for t, w in items:
            nt = norm(t)
            hit = None
            for sty, body in rows:
                nb = norm(body)
                if nb and (nt == nb or nb.startswith(nt[:14]) or nt.startswith(nb[:14])):
                    hit = (sty, body)
                    break
            if hit is None:
                miss.append((t, w, "该句在 .ass 里没找到（锚点没命中？）"))
                continue
            sty, body = hit
            if "\\c" in body:
                ok += 1
                print(f"  ✅ [{sty}] {w}")
            else:
                miss.append((t, w, f"上屏了但**不着色**（样式 {sty}）"))
        for t, w, why in miss:
            print(f"  ⛔ {why}")
            print(f"      卡面「{t}」／标色词「{w}」")
        bad_total += len(miss)
        print(f"  → 着色 {ok}／{len(items)}")

    print("=" * 66)
    print("全部着色 ✅" if bad_total == 0 else f"⛔ 有 {bad_total} 处未着色")
    return 0 if bad_total == 0 else 1


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.exit(main(sys.argv[1:]))
