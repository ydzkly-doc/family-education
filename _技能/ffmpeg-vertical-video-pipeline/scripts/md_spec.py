# -*- coding: utf-8 -*-
r"""
文案 MD → 剪辑单片段

按 `reference/md_authoring_guide.md` 的固定格式，解析文案 MD 里的「上屏方案」区块，
产出可直接并入剪辑单的字段（subs / subs_emph / punch / seq / marks / cover / hook / bgm）。

**创作者只维护 MD**；本模块负责把 MD 读成 spec。
`video_make.py --md 文案.md` 会自动调用它。

单独调试：
    python md_spec.py 文案.md          # 打印解析出的片段（JSON）
    python md_spec.py --selftest       # 解析逻辑自检（不需要外部文件）

支持的「版本」三选一（大小写/空格/写法差异都容错）：
    全字幕            → subs="all"
    金句 / 金句版      → subs=[强调句...]（只有这几句上字幕）
    全字幕 + 金句      → subs="all" + subs_emph=[强调句...]（这几句加大加粗）
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    from video_build_ass import WARM, WARM_DEEP
except Exception:                       # 允许脱离管道独立运行
    WARM, WARM_DEEP = "#C2703C", "#A8551F"

CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩"
DEFAULT_PUNCH_HOLD = 4.5                # 金句大字卡默认停留（秒）
DEFAULT_SEQ_HOLD = 2.5                  # 序号条默认停留（秒）
DEFAULT_HOOK_HOLD = 2.5                 # 开头钩子默认停留（秒）—— 与引擎侧默认一致
DEFAULT_CARD_HOLD = 3.0                 # 浅底文字卡默认停留（秒）
CARD_SIZE_BIG = 82                      # 「比字幕大一号」
CARD_SIZE_SMALL = 68                    # 「比字幕小一号」
DEFAULT_ZOOM = 0.06                     # 「画面轻微推近」的默认幅度（1.0 → 1.06）
END_CARD_HOLD = 2.0                     # 片尾定格卡（方便截图）
ENLARGE_SCALE = 1.12                    # "轻微放大" 的换算值

V_ALL, V_KOU, V_ALL_KOU = "all", "kou", "all_kou"
V_LABEL = {V_ALL: "全字幕", V_KOU: "金句", V_ALL_KOU: "全字幕 + 金句"}


# ==================== 区块切分 ====================
def _section(md: str, *names: str) -> str:
    """取标题含 names 之一的区块内容（到下一个同级或更高级标题为止）。"""
    lines = md.split("\n")
    for i, ln in enumerate(lines):
        m = re.match(r"^(#{1,4})\s*(.+?)\s*$", ln)
        if not m:
            continue
        lvl, title = len(m.group(1)), m.group(2)
        if any(n in title for n in names):
            buf = []
            for j in range(i + 1, len(lines)):
                m2 = re.match(r"^(#{1,4})\s+", lines[j])
                if m2 and len(m2.group(1)) <= lvl:
                    break
                buf.append(lines[j])
            return "\n".join(buf)
    return ""


def _subsections(block: str) -> dict:
    """把区块按 ### 切成 {子标题: 原始文本}"""
    out, cur, buf = {}, None, []
    for ln in block.split("\n"):
        m = re.match(r"^#{3,4}\s*(.+?)\s*$", ln)
        if m:
            if cur is not None:
                out[cur] = "\n".join(buf)
            cur, buf = m.group(1).strip(), []
        elif cur is not None:
            buf.append(ln)
    if cur is not None:
        out[cur] = "\n".join(buf)
    return out


def _pick(subs: dict, *names: str) -> str:
    """
    在子节里找标题含 names 之一的那一节。

    ⚠️ 命中名字**越长越优先**。否则会踩这个坑（实测）：
        「### 强调句（⭐ 金句版下，这 2 句就是全部会上底部字幕的句子）」
        标题里含「金句」二字，于是 `_pick(subs, "大字卡", "金句")` 会先命中它，
        把**强调句**当成大字卡解析，真正的「### 金句大字卡（居中）」反而读不到。
    顺序：先整键精确匹配 → 再按匹配到的名字长度取最长。
    """
    for n in names:
        if n in subs:
            return subs[n]
    best, best_len = "", -1
    for k, v in subs.items():
        for n in names:
            if n in k and len(n) > best_len:
                best, best_len = v, len(n)
    return best


def _items(block: str):
    """按 `1.` `2.` 切条目 → [[首行, 子行...], ...]"""
    items, cur = [], None
    for ln in block.split("\n"):
        m = re.match(r"^\s*(\d+)\s*[.、)]\s*(.+?)\s*$", ln)
        if m:
            cur = [m.group(2)]
            items.append(cur)
        elif cur is not None and ln.strip():
            cur.append(ln.strip())
    return items


# ==================== 小工具 ====================
def _anchors(s: str):
    """取「」里的文本（上屏/定位用）"""
    return [x.strip() for x in re.findall(r"「([^」]+)」", s) if x.strip()]


def _quoted(s: str):
    """取引号里的文本（兼容中英文引号）"""
    out = []
    for m in re.finditer(r"[“\"'‘]([^”\"'’「」]+)[”\"'’]", s):
        t = m.group(1).strip()
        if t:
            out.append(t)
    return out


def _hold(s: str, default: float) -> float:
    m = re.search(r"停\s*(?:约|留|顿)?\s*([\d.]+)\s*秒", s)
    return float(m.group(1)) if m else default


def _marks(desc: str, base_color: str, default_bold: bool = False):
    """从一句描述里抽标色规则：`"装的"标暖色加粗、轻微放大` → [{word,color,bold,scale}]

    default_bold：MD 没写"加粗"时是否默认加粗。
      ⚠️ 大字卡（punch）传 True —— 100px 居中大字上，标色词不加粗会显得单薄；
      字幕（subs/subs_emph）保持 False —— 写什么就是什么，避免整句变粗反而糊。
    """
    words = _quoted(desc)
    if not words:
        return []
    warm = any(w in desc for w in ("暖", "橙", "棕", "品牌色"))
    bold = ("加粗" in desc) or (default_bold and "不加粗" not in desc)
    scale = ENLARGE_SCALE if re.search(r"放大|变大", desc) else None
    out = []
    for w in words:
        m = {"word": w}
        if warm:
            m["color"] = base_color
        if bold:
            m["bold"] = True
        if scale:
            m["scale"] = scale
        out.append(m)
    return out


def _desc_of(head: str) -> str:
    """取 `→` 之后的描述部分；没有 `→` 就整句当描述"""
    return head.split("→", 1)[1] if "→" in head else head


# ==================== 各段解析 ====================
def parse_version(text: str) -> str:
    """三选一：全字幕 / 金句 / 全字幕 + 金句"""
    s = re.sub(r"[\s*`_]", "", text)
    if ("金句" not in s) and ("强调" not in s):
        return V_ALL
    if "全字幕" in s:
        return V_ALL_KOU
    return V_KOU


def _version_line(blk: str) -> str:
    """
    取「版本」那一行的内容。

    ⚠️ 为什么不能直接扫整块：区块里会有各种说明文字，一旦出现"全字幕"三个字
    （例如"相比全字幕版…"），`parse_version` 就会把**金句版误判成"全字幕+金句"**。
    所以优先只看"版本"那一行，取不到才退回整块前 500 字容错。
    """
    m = re.search(r"^\s*[-*]?\s*\**版本\**\s*[:：]\s*(.+?)\s*$", blk, re.M)
    return m.group(1) if m else ""


def parse_emph(block: str):
    """强调句列表 → [{anchor, style, marks}]"""
    out = []
    for it in _items(block):
        head = it[0]
        a = _anchors(head)
        if not a:
            continue
        desc = _desc_of(head)
        # `- 挂在这句：「…」` 优先当锚点（上屏文字与口播原话不同时用它）
        anchor = a[0]
        for sub in it[1:]:
            if "挂" in sub:
                a2 = _anchors(sub)
                if a2:
                    anchor = a2[0]
                    break
        item = {"anchor": anchor, "style": "强调"}
        mk = _marks(desc, WARM)
        if mk:
            item["marks"] = mk
        out.append(item)
    return out


def parse_punch(block: str):
    """金句大字卡 → [{text, marks, anchor, hold}]（含可选片尾定格卡）"""
    out, end_added = [], False
    for it in _items(block):
        head = it[0]
        txt = _anchors(head)
        if not txt:
            continue
        desc = _desc_of(head)
        anchor = None
        for sub in it[1:]:
            if "挂" in sub:
                a = _anchors(sub)
                if a:
                    anchor = a[0]
                    break
        card = {"text": txt[0]}
        mk = _marks(desc, WARM_DEEP, default_bold=True)
        if mk:
            card["marks"] = mk
        card["anchor"] = anchor or txt[0]     # 没写挂句就用文字自身
        card["hold"] = _hold(head, DEFAULT_PUNCH_HOLD)
        out.append(card)

        wants_end = any("回放" in s for s in it[1:]) or "回放" in head
        if wants_end and not end_added:
            end_card = {k: v for k, v in card.items() if k != "anchor"}
            end_card["at"] = "end"
            end_card["hold"] = END_CARD_HOLD
            end_card["to_end"] = True
            out.append(end_card)
            end_added = True
    return out


def parse_seq(block: str):
    """序号条 → [{text, anchor, hold}]"""
    texts, anchors = {}, {}
    for ln in block.split("\n"):
        for m in re.finditer(rf"([{CIRCLED}])\s*挂\s*[「“\"']([^」”\"']+)[」”\"']", ln):
            anchors[m.group(1)] = m.group(2).strip()
        if ("照抄" in ln) or ("文案" in ln):
            for m in re.finditer(rf"([{CIRCLED}])\s*([^{CIRCLED}\n]+)", ln):
                t = m.group(2).strip(" 　*｜|：:，,。")
                if t and m.group(1) not in texts:
                    texts[m.group(1)] = t
    out = []
    for n in CIRCLED:
        if n not in texts:
            continue
        item = {"text": f"{n} {texts[n]}", "hold": DEFAULT_SEQ_HOLD}
        if n in anchors:
            item["anchor"] = anchors[n]
        out.append(item)
    return out


def parse_marks(block: str):
    """全片标色 → [{word, color, bold}]"""
    words, out = [], []
    for ln in block.split("\n"):
        if not ln.strip():
            continue
        for w in _quoted(ln):
            if w not in words:
                words.append(w)
    for w in words:
        out.append({"word": w, "color": WARM, "bold": True})
    return out


def parse_cover(block: str):
    """封面 → {text}"""
    for ln in block.split("\n"):
        m = re.search(r"\*\*(.+?)\*\*", ln)
        if m:
            t = m.group(1).strip()
            if t:
                return {"text": t}
        a = _anchors(ln)
        if a:
            return {"text": a[0]}
    return None


def parse_hook(block: str):
    """
    开头钩子 → `spec["hook"]`（**单个对象**，不是列表）

    格式（见 `reference/md_authoring_guide.md`）：
        ### 开头钩子（前 3 秒大字，静音也看得见）
        - 「他是不是装的？」停约 2.5 秒
        - 「他是不是装的？」→ "装的"标暖色加粗；停约 2.5 秒     ← 想标色就加 → 描述

    ⭐ 钩子是**前 3 秒居中大字**：视频号/朋友圈是**静音自动播放**，前 3 秒只有大字能抓人。
    ⭐ 引擎侧会把它渲染成**不带淡入**（`anim=""`）—— 因为平台默认拿**视频第一帧**当封面，
       带淡入的话第一帧是完全透明的，封面就变成"纯画面无文字"了。
    """
    if not block or not block.strip():
        return None
    items = _items(block)
    head = items[0][0] if items and items[0] else ""
    if not head:
        head = (block.strip().splitlines() or [""])[0]
    # 取「」里的文案；没有就用弯引号；再没有就把整行去掉说明性括号当文案
    txt = _anchors(head) or _quoted(head)
    if not txt:
        t = re.sub(r"[（(][^）)]*[）)]", "", head).strip(" -—*·•1.、")
        if not t:
            return None
        txt = [t]
    hook = {"text": txt[0]}
    # 标色描述 = 首行 + 其后的缩进说明行（合并后一起提标色；「」里的文案不会被误当标色词）
    desc = _desc_of(head)
    if items and len(items[0]) > 1:
        desc += " " + " ".join(items[0][1:])
    mk = _marks(desc, WARM, default_bold=True)
    if mk:
        hook["marks"] = mk
    hook["hold"] = _hold(head, DEFAULT_HOOK_HOLD)
    return hook


def parse_cards(block: str):
    """
    浅底文字卡 → `spec["cards"] = [{text, anchor, hold, size?}]`

    格式：
        ### 浅底卡（画面下方浅底文字卡）
        1. 「我听到了，你现在很不想去」→ 停 3 秒；挂在「我听到了」
        2. 「今晚不用把所有原因说清」→ 挂在「我听到了」

    ⚠️ 必须用 `1.` `2.` **有序列表** —— 解析器只认这个（`-` 开头的行留给"文案照抄/挂句"这类说明）
    ⭐ 是**浅底文字卡**（浅米底 + 深字，落在画面下方），**不是**居中大字卡 —— 两者别混：
       大字卡走 `### 金句大字卡`（`punch`），这里走 `cards`。
    ⭐ 字号不用精确写：`比字幕大一号` / `大一点` / `小很多` 都能识；也可直接写 `字号 82`。
    ⚠️ 卡片文字若**不在口播里**（额外补充的话），**必须写"挂在「某句」"**，
       否则定位不到 —— 管道会打印可用字幕行让你改。
    """
    if not block or not block.strip():
        return []
    out = []
    for it in _items(block):
        head = it[0]
        txt = _anchors(head)
        if not txt:
            continue
        subs = it[1:]
        desc = _desc_of(head)
        if subs:
            desc += " " + " ".join(subs)
        card = {"text": txt[0]}
        # 「挂在「某句」」可能写在**条目行内**，也可能写在**缩进子行**里 —— 两处都找
        anchor = None
        for src in [head] + subs:
            if "挂" not in src:
                continue
            after = src.split("挂", 1)[1]          # 取"挂"之后的锚点，避免抓成卡面文字
            a = _anchors(after)
            if a:
                anchor = a[0]
                break
        card["anchor"] = anchor or txt[0]
        card["hold"] = _hold(head + " " + desc, DEFAULT_CARD_HOLD)
        m = re.search(r"字号\s*(\d+)", desc)
        if m:
            card["size"] = int(m.group(1))
        elif re.search(r"大一号|大一点|大一些", desc):
            card["size"] = CARD_SIZE_BIG
        elif re.search(r"小一号|小一点|小很多|小一些", desc):
            card["size"] = CARD_SIZE_SMALL
        mk = _marks(desc, WARM, default_bold=False)
        if mk:
            card["marks"] = mk
        out.append(card)
    return out


def parse_screen(block: str) -> dict:
    """
    画面处理 → `spec["zoom"]`（整片轻微推近，Ken Burns）

    格式：
        ### 画面
        - 轻微推近            ← 全片从 1.0 缓推到 1.06
        - 推近 0.08           ← 想更明显就给数值

    ⭐ 写着"画面轻微推近"是很多 MD 的习惯写法。**兜底**：即便这一节没写，
       只要整个「上屏方案」区块里出现过「画面轻微推近」，也会启用（见 parse_md）。
    """
    if not block or not block.strip():
        return {}
    if re.search(r"不推近|不做推近|不推|静止|固定机位", block):
        return {}
    m = re.search(r"推近\s*([\d.]+)", block)
    if m:
        try:
            return {"zoom": float(m.group(1))}
        except ValueError:
            pass
    if "推近" in block:
        return {"zoom": DEFAULT_ZOOM}
    return {}


def parse_bgm(block: str):
    """
    解析「### 背景音乐」子节 → spec["bgm"]。

    ⭐ **没有这一节 = 不垫 BGM**（BGM 默认不启用）。
    ⭐ **位置是参数**：`位置：头尾`（默认，只垫没有口播处）/ `位置：全程`（整片垫底 + 自动压低）。

    宽松写法都能认：
      - 曲目：轻音乐.mp3            → file（直接指定文件）
      - 风格：安静的钢琴             → style（按风格从曲库筛）
      - 位置：头尾 / 全程            → placement
      - 音量：比口播低约 22dB / -22  → gain（自动处理正负）
      - 压低：12                     → duck（仅「全程」用）
      - 定点压低：「某句」再压 6dB、0.5 秒 → dips
    """
    if not block or not block.strip():
        return None
    lines = [ln.strip().lstrip("-*·• \t").strip()
             for ln in block.strip().splitlines()]
    pairs = []
    for ln in lines:
        if not ln or ln.startswith("#"):
            continue
        m = re.match(r"^([^：:]{1,12})[：:]\s*(.*)$", ln)
        if m:
            pairs.append((m.group(1).strip(), m.group(2).strip()))

    low_all = block.lower()
    if not pairs:
        # 整节写成散文，例如「本节不垫背景音乐」
        return None
    if any(w in low_all[:80] for w in ("不垫", "不加", "不要背景", "无背景", "关闭背景")):
        return None

    def get(*keys, exclude=()):
        for k, v in pairs:
            if any(e in k for e in exclude):
                continue
            if any(w in k for w in keys):
                return v
        return ""

    none_words = ("无", "没有", "不垫", "不用", "-", "—", "none")

    def val(s):
        s = (s or "").strip()
        return "" if s.lower() in none_words else s

    file_v = val(get("曲目", "文件", "音乐", exclude=("风格",)))
    style_v = val(get("风格", "标签", "类型"))
    place_v = get("位置", "范围", "播放")
    gain_v = get("音量", "增益", exclude=("压低",))
    duck_v = get("压低", "duck", exclude=("定点",))
    dips_v = get("定点", "金句压低")

    cfg: dict = {}
    if file_v:
        cfg["file"] = file_v
    if style_v:
        cfg["style"] = style_v
    if not cfg:
        return None                      # 既没曲目也没风格 → 视作未启用

    if place_v:
        if re.search(r"全程|全片|整片|铺满|full", place_v):
            cfg["placement"] = "full"
        elif re.search(r"头尾|首尾|两头|开头和结尾|仅.{0,4}结尾", place_v):
            cfg["placement"] = "head_tail"

    def num(s):
        m = re.search(r"(-?\d+(?:\.\d+)?)", s or "")
        return float(m.group(1)) if m else None

    g = num(gain_v)
    if g is not None:
        # 「比口播低约 22dB」这种正数写法要转成负增益
        if g > 0 and re.search(r"低|减|下|小", gain_v):
            g = -g
        cfg["gain"] = g
    d = num(duck_v)
    if d is not None:
        cfg["duck"] = abs(d)

    if dips_v:
        dips = []
        for m in re.finditer(r"[「『\"]([^」』\"]+)[」』\"]\s*([^「『\n]{0,40})", dips_v):
            anchor, rest = m.group(1).strip(), m.group(2)
            extra, hold = 6.0, 0.5
            nums = re.findall(r"(\d+(?:\.\d+)?)\s*(dB|分贝|秒|s)?", rest)
            for n, unit in nums:
                if unit in ("秒", "s"):
                    hold = float(n)
                else:
                    extra = abs(float(n))
            dips.append({"anchor": anchor, "extra": extra, "hold": hold})
        if dips:
            cfg["dips"] = dips
    return cfg


# ==================== 主入口 ====================
def parse_md(path: str) -> dict:
    """读文案 MD → 返回剪辑单片段（可直接 update 进 spec）。"""
    with open(path, encoding="utf-8-sig") as f:
        md = f.read()

    blk = _section(md, "上屏方案")
    if not blk.strip():
        raise ValueError(
            f"MD 里找不到「上屏方案」区块：{path}\n"
            f"  → 格式见 reference/md_authoring_guide.md（标题写 `## 上屏方案`）")

    subs_blk = _subsections(blk)
    ver = parse_version(_pick(subs_blk, "版本")
                        or _version_line(blk) or blk[:500])
    emph = parse_emph(_pick(subs_blk, "强调句"))
    punch = parse_punch(_pick(subs_blk, "大字卡", "金句"))
    seq = parse_seq(_pick(subs_blk, "序号条", "序号"))
    marks = parse_marks(_pick(subs_blk, "全片标色", "标色"))
    cover = parse_cover(_pick(subs_blk, "封面"))
    hook = parse_hook(_pick(subs_blk, "开头钩子", "钩子", "开头大字"))
    cards = parse_cards(_pick(subs_blk, "浅底卡", "小卡", "台词卡",
                              "话术卡", "小字卡", "祝愿卡", "文字卡"))
    screen = parse_screen(_pick(subs_blk, "画面", "镜头", "运镜"))
    if not screen and re.search(r"画面[^。\n]{0,8}推近|轻微推近", blk):
        # 兜底：老 MD 习惯把这句写在金句卡条目里，不该因为位置不同就失效
        screen = {"zoom": DEFAULT_ZOOM}
    bgm = parse_bgm(_pick(subs_blk, "背景音乐", "BGM", "配乐", "背景乐"))

    out: dict = {}
    if ver == V_KOU:
        # 金句版：只有这几句上字幕
        rows = []
        for e in emph:
            row = {"anchor": e["anchor"]}
            if e.get("marks"):
                row["marks"] = e["marks"]
            rows.append(row)
        out["subs"] = rows if rows else "none"
        # ⭐ 金句版这几句是**唯一的视觉文字**，默认用「强调」样式（更醒目）；
        #    它们本来就在 subs 里，apply_subs_emph 会正常叠加。
        if emph:
            out["subs_emph"] = emph
    else:
        out["subs"] = "all"
        if emph:
            out["subs_emph"] = emph

    if punch:
        out["punch"] = punch
    if seq:
        out["seq"] = seq
    if marks:
        out["marks"] = marks
    if cover:
        out["cover"] = cover
    if hook:
        out["hook"] = hook
    if cards:
        out["cards"] = cards
    if screen.get("zoom"):
        out["zoom"] = screen["zoom"]
    if bgm:
        # ⭐ 只有 MD 里写了「背景音乐」子节、且给了曲目/风格，才会垫 BGM
        out["bgm"] = bgm

    out["_from_md"] = {
        "file": os.path.abspath(path),
        "version": V_LABEL[ver],
        "counts": {"强调句": len(emph), "大字卡": len(punch),
                   "序号条": len(seq), "标色": len(marks),
                   "封面": 1 if cover else 0,
                   "开头钩子": 1 if hook else 0,
                   "浅底卡": len(cards),
                   "画面推近": 1 if screen.get("zoom") else 0,
                   "背景音乐": 1 if bgm else 0},
    }
    return out


# ==================== 逐字稿抽取 ====================
def extract_script(md_path: str) -> str:
    """从 MD 的「口播文案」段抽出逐字稿（一行一句）。

    剥掉方括号拍摄提示与 markdown 标记 —— 结果可直接当管道的 `--script` 用（一行一句）。
    """
    with open(md_path, encoding="utf-8-sig") as f:
        md = f.read()
    blk = _section(md, "口播文案", "口播脚本")
    if not blk.strip():
        return ""
    out = []
    for ln in blk.split("\n"):
        s = ln.strip()
        if not s:
            continue
        if s.startswith("#"):                       # 到下一节标题就停
            break
        if s.startswith((">", "|", "```")):
            continue
        if set(s) <= {"-", "—", "–", "*", "_"}:     # 分隔线
            continue
        s = re.sub(r"^【[^】]*】\s*", "", s)         # 行首方括号提示
        s = re.sub(r"【[^】]*】", "", s)             # 行内残留提示
        s = s.replace("**", "").strip().strip("　 ")
        if s:
            out.append(s)
    return "\n".join(out)


# ==================== 自检 ====================
SAMPLE = """# 测试文案

# 【照着剪】

## 四、上屏方案

- **版本**：**全字幕 + 金句强调**（全程都有底部字幕，其中 2 句用更大的强调样式）
- **字幕位置**：画面下方

### 开头钩子（前 3 秒大字，静音也看得见）
- 「他是不是装的？」→ "装的"标暖色加粗；停约 2.6 秒

### 强调句（⭐ 金句版下，这 2 句就是**全部**会上底部字幕的句子）
1. 「我儿子，会不会是装的」 → "装的"标暖色加粗、轻微放大
2. 「那点力气，本来该用来帮孩子的」 → "帮孩子"标暖色加粗

### 金句大字卡（居中）
1. 「检查没查出来，不等于孩子在装」 → "不等于孩子在装"标暖橙/暖棕系、其余白色；停约 3 秒
   - 挂在这句：「检查没查出来，不等于孩子在装」
   - 结尾再回放一帧同一张卡（方便截图）

### 序号条
- 文案照抄：**① 多久了　② 影响多大　③ 有没有危险情况**
- 挂句：① 挂「第一个，看多久了」 ② 挂「第二个，看影响多大」 ③ 挂「第三个，看有没有更危险的情况」

### 浅底卡（画面下方浅底文字卡）
1. 「我听到了，你现在很不想去」→ 停 3 秒；挂在「我听到了」
2. 「今晚不用把所有原因说清」→ 比字幕大一点；挂在「我听到了」

### 画面
- 轻微推近

### 全片标色
- "装的"、"帮孩子" → 暖色加粗（其余不加）

### 封面
- 大字：**不等于孩子在装**（备选：我以为是装的）

### 背景音乐
- 曲目：轻音乐_安静.mp3
- 位置：头尾
- 音量：比口播低约 22dB
"""

SAMPLE_KOU = SAMPLE.replace("**全字幕 + 金句强调**", "**金句版**")
SAMPLE_ALL = SAMPLE.replace("**全字幕 + 金句强调**", "**全字幕**")


def selftest() -> int:
    bad = 0

    def chk(cond, msg):
        nonlocal bad
        print(("  ✅ " if cond else "  ❌ ") + msg)
        if not cond:
            bad += 1

    print("【1】版本识别")
    chk(parse_version("全字幕 + 金句强调") == V_ALL_KOU, "全字幕 + 金句强调 → all_kou")
    chk(parse_version("全字幕+金句") == V_ALL_KOU, "无空格写法也认")
    chk(parse_version("金句版") == V_KOU, "金句版 → kou")
    chk(parse_version("金句") == V_KOU, "金句 → kou")
    chk(parse_version("全字幕") == V_ALL, "全字幕 → all")
    chk(parse_version("（三选一，必须写）") == V_KOU or True, "空/无效写法不崩")

    print("【2】强调句")
    e = parse_emph(_pick(_subsections(_section(SAMPLE, "上屏方案")), "强调句"))
    chk(len(e) == 2, f"解析出 2 条（实际 {len(e)}）")
    chk(e[0]["anchor"] == "我儿子，会不会是装的", "锚点取「」内文本")
    chk(e[0]["marks"][0]["word"] == "装的", "标色词正确")
    chk(e[0]["marks"][0].get("bold") is True, "识别「加粗」")
    chk(abs(e[0]["marks"][0].get("scale", 0) - ENLARGE_SCALE) < 1e-6, "识别「轻微放大」")
    chk(e[1]["marks"][0]["word"] == "帮孩子", "第二条标色词正确")

    print("【3】金句大字卡")
    sub = _subsections(_section(SAMPLE, "上屏方案"))
    # ⚠️ 回归用例：真实 MD 的强调句标题常含「金句版」字样，
    #    所以这里必须用**与 parse_md 相同的候选名**来测——
    #    否则「金句」二字会把「强调句」节抢走，大字卡被解析成强调句（曾经踩过）。
    blk = _pick(sub, "大字卡", "金句")
    chk("检查没查出来" in blk, "强调句标题含「金句」时，不会抢走大字卡节")
    chk("我儿子" not in blk, "大字卡节里不该混进强调句内容")
    p = parse_punch(blk)
    chk(len(p) == 2, f"1 张卡 + 1 张片尾定格卡（实际 {len(p)}）")
    chk(p[0]["text"] == "检查没查出来，不等于孩子在装", "卡面文字正确")
    chk(p[0]["anchor"] == "检查没查出来，不等于孩子在装", "「挂在这句」当锚点")
    chk(abs(p[0]["hold"] - 3.0) < 1e-6, "识别「停约 3 秒」")
    chk(p[0]["marks"][0]["color"] == WARM_DEEP, "大字卡用深暖色")
    chk(p[0]["marks"][0].get("bold") is True, "大字卡标色默认加粗（MD 没写也加）")
    chk(p[1].get("at") == "end" and p[1].get("to_end") is True, "片尾定格卡正确")
    chk("anchor" not in p[1], "片尾卡不带 anchor")

    print("【4】序号条")
    s = parse_seq(_pick(_subsections(_section(SAMPLE, "上屏方案")), "序号条"))
    chk(len(s) == 3, f"解析出 3 条（实际 {len(s)}）")
    chk(s[0]["text"] == "① 多久了", f"文案带序号：{s[0]['text']}")
    chk(s[0]["anchor"] == "第一个，看多久了", "挂句正确")
    chk(s[2]["anchor"] == "第三个，看有没有更危险的情况", "第三条挂句正确")

    print("【5】全片标色 / 封面")
    mk = parse_marks(_pick(_subsections(_section(SAMPLE, "上屏方案")), "全片标色"))
    chk([m["word"] for m in mk] == ["装的", "帮孩子"], f"标色词：{[m['word'] for m in mk]}")
    cv = parse_cover(_pick(_subsections(_section(SAMPLE, "上屏方案")), "封面"))
    chk(cv and cv["text"] == "不等于孩子在装", f"封面：{cv}")

    print("【5b】开头钩子（⭐ 前 3 秒大字，静音场景靠它抓人）")
    hk = parse_hook(_pick(sub, "开头钩子", "钩子", "开头大字"))
    chk(hk is not None, "能解析出 hook")
    chk(hk and hk.get("text") == "他是不是装的？", f'文案：{hk.get("text") if hk else None}')
    chk(hk and abs(hk.get("hold", 0) - 2.6) < 1e-6, f'停约 2.6 秒：{hk.get("hold") if hk else None}')
    chk(hk and hk.get("marks") and hk["marks"][0]["word"] == "装的",
        f'标色词：{hk.get("marks") if hk else None}')
    chk(parse_hook("") is None, "没有这一节 → 不启用（默认）")
    chk(parse_hook("- 「他是不是装的？」") .get("hold") == DEFAULT_HOOK_HOLD,
        "没写时长 → 用默认 2.5 秒")
    chk(parse_hook("- 「他是不是装的？」")["text"] == "他是不是装的？",
        "只写锚点、不写描述也能解析")
    chk(parse_hook("- 他是不是装的？（停 3 秒）")["text"] == "他是不是装的？",
        "没加「」时也能解析（去说明性括号）")

    print("【5c】浅底文字卡 + 画面推近")
    cd = parse_cards(_pick(sub, "浅底卡", "小卡", "台词卡", "话术卡",
                           "小字卡", "祝愿卡", "文字卡"))
    chk(len(cd) == 2, f"解析出 2 张浅底卡（实际 {len(cd)}）")
    chk(cd and cd[0]["text"] == "我听到了，你现在很不想去", f'文案：{cd[0]["text"] if cd else None}')
    chk(cd and abs(cd[0]["hold"] - 3.0) < 1e-6, f'停 3 秒：{cd[0]["hold"] if cd else None}')
    chk(cd and cd[0]["anchor"] == "我听到了", f'"挂"句当锚点：{cd[0]["anchor"] if cd else None}')
    chk(cd and cd[1].get("size") == CARD_SIZE_BIG,
        f'"比字幕大一点" → {CARD_SIZE_BIG}：{cd[1].get("size") if len(cd) > 1 else None}')
    chk(parse_cards("1. 「甲」→ 字号 90")[0].get("size") == 90, "显式「字号 90」优先")
    chk(parse_cards("1. 「甲」→ 小很多")[0].get("size") == CARD_SIZE_SMALL,
        f'"小很多" → {CARD_SIZE_SMALL}')
    chk(parse_cards("") == [], "没有这一节 → 空（默认）")
    chk(parse_cards("1. 「甲」")[0].get("size") is None,
        "没提字号 → 用样式默认（不写死）")
    chk(parse_cards("- 「甲」") == [],
        "用 `-` 无序列表 → 解析不出（必须 1. 2. 有序列表）")

    sc = parse_screen(_pick(sub, "画面", "镜头", "运镜"))
    chk(abs(sc.get("zoom", 0) - DEFAULT_ZOOM) < 1e-6,
        f'"轻微推近" → zoom={DEFAULT_ZOOM}，实际 {sc.get("zoom")}')
    chk(abs(parse_screen("- 推近 0.1").get("zoom", 0) - 0.1) < 1e-6, "可显式给幅度")
    chk(parse_screen("- 不推近") == {}, "写「不推近」→ 关闭")
    chk(parse_screen("") == {}, "没有这一节 → 关闭（默认）")

    print("【5d】背景音乐（⭐ 默认不启用；位置是参数）")
    bg = parse_bgm(_pick(sub, "背景音乐", "BGM", "配乐", "背景乐"))
    chk(bg is not None, "能解析出 bgm")
    chk(bg.get("file") == "轻音乐_安静.mp3", f'曲目：{bg.get("file")}')
    chk(bg.get("placement") == "head_tail", f'位置「头尾」→ head_tail：{bg.get("placement")}')
    chk(abs(bg.get("gain", 0) + 22) < 1e-6, f'「比口播低约 22dB」→ -22：{bg.get("gain")}')
    chk(parse_bgm("") is None, "没有「背景音乐」节 → 不启用（默认）")
    chk(parse_bgm("本节不垫背景音乐") is None, "写「不垫」→ 不启用")
    chk(parse_bgm("- 位置：头尾") is None, "只写位置、没给曲目/风格 → 不启用")
    b2 = parse_bgm("- 风格：安静的钢琴\n- 位置：全程\n- 压低：10\n"
                   "- 定点压低：「检查没查出来」再压 6dB、0.5 秒")
    chk(b2 and b2.get("style") == "安静的钢琴", f"风格：{b2}")
    chk(b2.get("placement") == "full", "「全程」→ full")
    chk(b2.get("duck") == 10.0, f'压低 10：{b2.get("duck")}')
    chk(len(b2.get("dips") or []) == 1
        and b2["dips"][0]["anchor"] == "检查没查出来", f'dips：{b2.get("dips")}')
    chk(abs(b2["dips"][0]["extra"] - 6) < 1e-6, "定点压低量 = 6dB")
    chk(abs(b2["dips"][0]["hold"] - 0.5) < 1e-6, "定点时长 = 0.5s")
    chk(parse_bgm("- 曲目：x.mp3\n- 压低：8")["duck"] == 8.0,
        "「压低」不会被「定点压低」抢走")

    print("【6】三种版本的产出差异")
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        for name, src, want in (("全字幕+金句", SAMPLE, "all"),
                                ("金句版", SAMPLE_KOU, "list"),
                                ("全字幕", SAMPLE_ALL, "all")):
            fp = os.path.join(d, f"{name}.md")
            with open(fp, "w", encoding="utf-8") as f:
                f.write(src)
            r = parse_md(fp)
            if want == "all":
                chk(r["subs"] == "all", f"{name} → subs=all")
            else:
                chk(isinstance(r["subs"], list) and len(r["subs"]) == 2,
                    f"{name} → subs=列表(2 句)")
            chk(len(r.get("punch") or []) == 2, f"{name} → 大字卡 2 张")
            chk(len(r.get("seq") or []) == 3, f"{name} → 序号条 3 条")
            if want == "all":
                chk("subs_emph" in r, f"{name} → 有 subs_emph（不是死板砍掉）")
            else:
                # ⭐ 金句版：这几句是**唯一上屏文字**，必须带「强调」样式，别掉成常规字幕
                chk("subs_emph" in r, f"{name} → 金句句带 subs_emph（样式不丢）")
                chk(all(x.get("style") == "强调" for x in r["subs_emph"]),
                    f"{name} → 金句句样式 = 强调")
                chk(len(r["subs_emph"]) == len(r["subs"]),
                    f"{name} → subs 与 subs_emph 句数一致")

        # ⭐ 版本判断只看「版本」那一行：正文里出现"全字幕"字样不得干扰
        fp2 = os.path.join(d, "noise.md")
        with open(fp2, "w", encoding="utf-8") as f:
            f.write(SAMPLE_KOU.replace(
                "### 强调句",
                "- **字幕位置**：画面下方（相比全字幕版更干净）\n\n### 强调句"))
        r2 = parse_md(fp2)
        chk(isinstance(r2["subs"], list),
            "正文含「全字幕」字样 → 仍判为金句版（不被干扰）")
        chk((r2.get("_from_md") or {}).get("version") == "金句",
            "版本标注 = 金句")

    print("【7】异常处理")
    with tempfile.TemporaryDirectory() as d:
        fp = os.path.join(d, "bad.md")
        with open(fp, "w", encoding="utf-8") as f:
            f.write("# 只有口播稿\n\n没有上屏方案区块。\n")
        try:
            parse_md(fp)
            chk(False, "缺「上屏方案」应该报错")
        except ValueError as ex:
            chk("上屏方案" in str(ex), "缺「上屏方案」→ 明确报错（不静默）")

    print("【8】逐字稿抽取")
    sample_script = """# 视频号文案 · 发布第1条《测试》

# 【照着念】

## 二、口播文案

【看着镜头，像跟人聊天那样，平着说】

那阵子我儿子老喊肚子疼。

有时候是头疼。

【停一下，语气放平】

【★金句】检查没查出来，不等于孩子在装。

【☆】那点力气，本来该用来帮孩子的。

---

## 三、提词器文案（全选复制）

这一节不该被抽进去。
"""
    with tempfile.TemporaryDirectory() as d:
        fp = os.path.join(d, "s.md")
        with open(fp, "w", encoding="utf-8") as f:
            f.write(sample_script)
        got = extract_script(fp).split("\n")
        chk(len(got) == 4, f"抽出 4 句（实际 {len(got)}）：{got}")
        chk(got[0] == "那阵子我儿子老喊肚子疼。", "第一句正确")
        chk(not any("【" in g for g in got), "方括号提示已剥净")
        chk(got[2] == "检查没查出来，不等于孩子在装。", "★金句前缀已剥掉、台词保留")
        chk(not any("提词器" in g for g in got), "没有串到下一节（提词器）")
        chk(not any("---" in g for g in got), "分隔线已过滤")

    print()
    print(f"自检结果：{'全部通过 ✅' if bad == 0 else f'{bad} 项失败 ❌'}")
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description="文案 MD → 剪辑单片段")
    ap.add_argument("md", nargs="?", help="文案 MD 路径")
    ap.add_argument("--selftest", action="store_true", help="解析逻辑自检（不需外部文件）")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())
    if not args.md:
        ap.error("给一个文案 MD 路径，或用 --selftest")
    print(json.dumps(parse_md(args.md), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
