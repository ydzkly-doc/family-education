# -*- coding: utf-8 -*-
"""
BGM 轨道 —— 背景音乐混入

⭐ 设计约定（2026-09-24 与用户确认，不可擅自更改）：
  1. **默认不启用**：spec["bgm"] 为 None / 未给 → 完全不混音乐。
     判据：**需要「额外素材」的能力一律默认关**（与 punch / cover / hook 同惯例），
     而「对已有素材做处理」的能力默认开（audio.enabled / visual.enabled / cut_silence）。
  2. **来源两种**：`file` 直接指定文件，或 `style` 按风格从曲库筛。
  3. **默认只垫「头尾没有口播的段落」**（placement="head_tail"）；
     需要全程垫底当氛围时用 placement="full"（会自动 ducking 压低）。
  4. **文件找不到 / 风格筛不到 → 报错停下，绝不静默跳过**。
     静默跳过会让人以为垫上了 BGM，出片才发现。
  5. **不自动扫素材目录里的音频**（放进去的可能只是参考素材，自动垫上会出乎意料）。

曲库位置（按优先级，两个都不存在就是「没曲库」）：
    篇级   {文案目录}/_素材/bgm/
    项目级 {项目根}/_资产/bgm/     ← 跨系列复用，推荐放这里
风格标注靠曲库目录下的 `曲库.md`（表格：文件 | 风格 | 情绪 | 时长 | 适用）；
没有该文件时退化为**按文件名关键词**匹配。

⛔ 不联网下载音乐（版权风险）——曲库为空时给出清单让人补，不自己找。

⛔ 混音必须发生在 loudnorm **之前**：
   否则 loudnorm 测的是「没混 BGM 的信号」，成片响度必然超标。
   故主管道走两阶段：Stage A 混音输出 WAV（无损）→ 测量 → Stage B 上 loudnorm。

用法（自检 / 查曲库）：
  python video_bgm.py --selftest
  python video_bgm.py --list                     # 列曲库
  python video_bgm.py --pick "安静的钢琴"          # 试试风格筛
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

AUDIO_EXTS = (".mp3", ".m4a", ".aac", ".wav", ".flac", ".ogg", ".opus", ".wma")
INDEX_NAME = "曲库.md"

# 交接处默认淡入/淡出（BGM 与口播交界处，避免"啪"地切掉）
HANDOFF = 0.5


def db2lin(db: float) -> float:
    return round(10 ** (float(db) / 20.0), 6)


def ffmpeg() -> str:
    import paths
    return paths.ffmpeg_path()


def run(args, cwd=None, label=""):
    if label:
        print(f"    · {label}")
    return subprocess.run(args, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", cwd=cwd)


# ============================ 曲库 ============================
def project_root(start: str) -> str:
    """向上找含 .workbuddy 的目录，作为项目根（曲库放它的 _资产 下）"""
    d = os.path.abspath(start)
    for _ in range(8):
        if os.path.isdir(os.path.join(d, ".workbuddy")):
            return d
        nd = os.path.dirname(d)
        if nd == d:
            break
        d = nd
    return os.path.abspath(start)


def bgm_dirs(*hints: str) -> list[str]:
    """
    返回**已存在**的曲库目录（按优先级）。
    hints 可传文案目录 / 素材目录，用于推断篇级曲库。
    """
    out, bases = [], []
    for h in hints:
        if not h:
            continue
        base = h if os.path.isdir(h) else os.path.dirname(os.path.abspath(h))
        bases.append(base)
        for cand in (os.path.join(base, "_素材", "bgm"),
                     os.path.join(base, "bgm")):
            if os.path.isdir(cand) and cand not in out:
                out.append(cand)
    root = project_root(bases[0] if bases else os.getcwd())
    proj = os.path.join(root, "_资产", "bgm")
    if os.path.isdir(proj) and proj not in out:
        out.append(proj)
    return out


def _read_index(d: str) -> list[dict]:
    """读曲库目录下的 曲库.md，解析 markdown 表格"""
    p = os.path.join(d, INDEX_NAME)
    if not os.path.isfile(p):
        return []
    rows = []
    try:
        txt = open(p, encoding="utf-8-sig").read()
    except Exception:
        return []
    for ln in txt.splitlines():
        ln = ln.strip()
        if not ln.startswith("|"):
            continue
        cells = [c.strip() for c in ln.strip("|").split("|")]
        if len(cells) < 2:
            continue
        # 跳过分隔行与表头
        if set("".join(cells)) <= set("-: "):
            continue
        if cells[0] in ("文件", "文件名", "曲目"):
            continue
        rows.append({"file": cells[0],
                     "style": " ".join(cells[1:3]),
                     "dur": cells[3] if len(cells) > 3 else "",
                     "use": cells[4] if len(cells) > 4 else ""})
    return rows


_NOISE = ("bgm", "music", "背景", "音乐", "配乐", "final", "new", "副本", "copy")


def _tokens(s: str) -> list[str]:
    parts = re.split(r"[\s、，,／/｜|·\-—_\.]+", str(s))
    return [p.strip() for p in parts if p.strip()]


def scan(dirs: list[str]) -> list[dict]:
    """扫曲库，返回 [{path,name,dir,text,indexed}]，text = 风格描述（供匹配）"""
    tracks = []
    for d in dirs:
        idx = _read_index(d)
        by_name = {r["file"]: r for r in idx}
        files = sorted(f for f in os.listdir(d)
                       if not f.startswith("_")        # 与素材目录同一惯例：_ 开头是过程产物
                       and f.lower().endswith(AUDIO_EXTS)
                       and os.path.isfile(os.path.join(d, f)))
        for f in files:
            meta = by_name.get(f)
            stem = os.path.splitext(f)[0]
            if meta:
                text = f"{meta['style']} {meta['use']} {stem}"
            else:
                text = stem.replace("_", " ")
            tracks.append({"path": os.path.join(d, f), "name": f, "dir": d,
                           "text": text.lower(), "indexed": bool(meta)})
    return tracks


def match(tracks: list[dict], style: str) -> list[tuple[float, list[str], dict]]:
    """
    风格匹配。打分规则（**中文没分隔符，整串匹配会全部落空，故必须做滑窗**）：

      · 词整体命中 → 记 1 分
      · 否则，若该词是中文且 ≥2 字 → 取 **2 字滑窗**，按命中比例记分
        （例：「安静的钢琴」→ 安静/静的/的钢/钢琴，命中「安静」「钢琴」→ 0.3 分）

    **命中多者优先**，同分按文件名排序（保证可复现）。
    返回 [(score, hits, track), ...] 降序。
    """
    words = [w.lower() for w in _tokens(style)]
    if not words:
        return []
    scored = []
    for t in tracks:
        text = t["text"]
        score, hits = 0.0, []
        for w in words:
            if w in text:
                score += 1.0
                hits.append(w)
                continue
            if len(w) >= 2 and re.search(r"[\u4e00-\u9fff]", w):
                grams = [w[i:i + 2] for i in range(len(w) - 1)]
                got = [g for g in grams if g in text]
                if got:
                    score += 0.6 * len(got) / len(grams)
                    hits.extend(got)
        scored.append((round(score, 4), hits, t))
    scored.sort(key=lambda x: (-x[0], x[2]["name"]))
    return scored


def resolve_file(name: str, dirs: list[str], extra: str | None = None) -> str | None:
    """解析指定文件：绝对路径 → 原样；否则依次在 extra / 曲库目录 里找"""
    if not name:
        return None
    if os.path.isabs(name):
        return name if os.path.isfile(name) else None
    for d in ([extra] if extra else []) + list(dirs):
        if not d:
            continue
        p = os.path.join(d, name)
        if os.path.isfile(p):
            return p
    return None


def resolve(cfg: dict, dirs: list[str], extra_dir: str | None = None):
    """
    定曲目。返回 (path, note)；失败返回 (None, 错误说明)
    ⛔ 失败**不静默**——上层据此报错停下。
    """
    file_name = (cfg.get("file") or "").strip()
    style = (cfg.get("style") or "").strip()

    if file_name:
        p = resolve_file(file_name, dirs, extra_dir)
        if not p:
            return None, (f"指定的曲目「{file_name}」找不到。\n"
                          f"       已查找：{extra_dir or '-'} 与曲库目录 "
                          f"{'、'.join(dirs) if dirs else '（无）'}")
        return p, f"指定文件：{os.path.basename(p)}"

    if style:
        tracks = scan(dirs)
        if not tracks:
            return None, (f"要按风格「{style}」筛，但**曲库是空的**。\n"
                          f"       已扫描：{'、'.join(dirs) if dirs else '（无曲库目录）'}\n"
                          f"       → 把音乐放进 `_资产/bgm/`（项目级）或 `<本篇>/_素材/bgm/`，\n"
                          f"          并加一个 `{INDEX_NAME}` 标注风格，格式：\n"
                          f"          | 文件 | 风格 | 情绪 | 时长 | 适用 |\n"
                          f"          | 钢琴_安静_60s.mp3 | 钢琴 安静 治愈 | 平静 | 62s | 口播垫底 |\n"
                          f"          ⛔ 本工具不联网下载音乐（版权风险），需要你提供。")
        ranked = match(tracks, style)
        best = ranked[0]
        if best[0] <= 0:
            names = "、".join(f"{t['name']}" for t in ranked[:6])
            return None, (f"曲库里没有匹配风格「{style}」的曲子。\n"
                          f"       曲库现有：{names}\n"
                          f"       → 要么换风格词，要么把合适的曲子放进曲库，"
                          f"要么改用 `file` 直接指定")
        hits = "、".join(dict.fromkeys(best[1]))
        return best[2]["path"], (f"按风格「{style}」筛中：{best[2]['name']}"
                                 f"（命中「{hits}」，共 {len(tracks)} 首候选）")

    return None, ("bgm 里既没给 `file` 也没给 `style`——不知道该用哪首曲子。\n"
                  "       → 二选一：`file: \"xxx.mp3\"` 或 `style: \"安静的钢琴\"`")


# ============================ 区间 ============================
def voice_bounds(lines, total: float) -> tuple[float, float]:
    """
    整片的「人声范围」= 第一句字幕起点 ~ 最后一句字幕终点。
    头尾无人声区间 = [0, 起点] 与 [终点, 片长]。
    """
    if lines:
        return float(lines[0]["start"]), float(lines[-1]["end"])
    return 0.0, float(total)


def _merge_spans(spans, gap: float = 0.5, total: float | None = None):
    """把零散区间合并（间隔 < gap 的并成一段），并裁剪到 [0, total]"""
    out = []
    for s, e in sorted(spans):
        if total is not None:
            s, e = max(0.0, s), min(float(total), e)
        if e - s < 0.05:
            continue
        if out and s - out[-1][1] <= gap:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return [(round(a, 3), round(b, 3)) for a, b in out]


def plan(cfg: dict, lines, total: float, dirs: list[str],
         extra_dir: str | None = None) -> dict:
    """
    产出混音计划。**失败抛 ValueError**（错误信息里附上怎么办），
    由调用方决定停下——绝不静默产出"没有 BGM 的成片"。
    """
    if not cfg or cfg.get("enabled", True) is False:
        return {"skip": True, "reason": "未启用"}

    path, note = resolve(cfg, dirs, extra_dir)
    if not path:
        raise ValueError(note)

    placement = str(cfg.get("placement") or "head_tail")
    if placement in ("头尾", "head", "head_tail", "首尾"):
        placement = "head_tail"
    elif placement in ("全程", "full", "全片"):
        placement = "full"

    gain = float(cfg.get("gain", -24.0))
    fade_in = float(cfg.get("fade_in", 1.0))
    fade_out = float(cfg.get("fade_out", 2.0))
    handoff = float(cfg.get("handoff", HANDOFF))
    min_len = float(cfg.get("min_len", 1.2))

    p = {"skip": False, "path": path, "name": os.path.basename(path),
         "note": note, "placement": placement, "gain": gain,
         "fade_in": fade_in, "fade_out": fade_out, "handoff": handoff,
         "loop": bool(cfg.get("loop", True)), "total": float(total),
         "duck": float(cfg.get("duck", 12.0)),
         "head": None, "tail": None, "dips": []}

    if placement == "full":
        p["region"] = (0.0, float(total))
        # ⭐ 自动压低（ducking）用**人声区间音量包络**实现，不用 sidechaincompress。
        #    原因（实测）：sidechaincompress 在本机构的信号下只压得动 ~2.5dB
        #    —— threshold / ratio / level_in 都标定过，达不到 12dB 的量；
        #    而 ASR 本来就给出**精确的人声区间** → 直接写音量包络更可控、可验证。
        #    区间前后各留 lead 秒，让人声起音之前 BGM 就退下去（否则第一个字会被盖）。
        lead = float(cfg.get("duck_lead", 0.08))
        p["duck_lead"] = lead
        p["duck_spans"] = _merge_spans(
            [(float(l["start"]) - lead, float(l["end"]) + lead)
             for l in (lines or [])],
            gap=float(cfg.get("duck_merge", 0.5)), total=total)
        if not p["duck_spans"]:
            print("    ⚠️ 没有可用的字幕时间码 → **无法自动压低**，"
                  "BGM 会全程同音量（可能盖住人声）。建议给 --script 或先跑 ASR。")
    else:
        v_start, v_end = voice_bounds(lines, total)
        # 显式覆盖优先
        if cfg.get("head_s") is not None:
            v_start = float(cfg["head_s"])
        if cfg.get("tail_s") is not None:
            v_end = float(cfg["tail_s"])
        if v_start >= min_len:
            p["head"] = (0.0, v_start)
        if total - v_end >= min_len:
            p["tail"] = (v_end, float(total))
        if not p["head"] and not p["tail"]:
            raise ValueError(
                f"头尾没有足够长的无人声段落（头 {v_start:.1f}s / "
                f"尾 {total - v_end:.1f}s，均短于 {min_len}s），垫上去会一响就被切掉。\n"
                f"       → 要么改用 `placement: \"full\"`（全程垫底 + 自动压低），\n"
                f"          要么把 `min_len` 调小，要么这句就不加 BGM")

    # 定点额外压低（某句话那半秒）
    for d in (cfg.get("dips") or []):
        if not isinstance(d, dict):
            continue
        se, err = _dip_span(d, lines)
        if se is None:
            print(f"    ⚠️ BGM 定点压低「{str(d.get('anchor') or d.get('start'))[:18]}」"
                  f"跳过：{err}")
            continue
        p["dips"].append({"span": se, "extra": float(d.get("extra", 6.0))})
    return p


def _dip_span(d: dict, lines):
    if d.get("start") is not None:
        s = float(d["start"])
        return (s, s + float(d.get("hold", 0.5))), None
    if d.get("anchor"):
        key = re.sub(r"[\s，。！？、,.!?；：“”\"'（）()「」]", "",
                     str(d["anchor"]))
        for ln in (lines or []):
            t = re.sub(r"[\s，。！？、,.!?；：“”\"'（）()「」]", "", ln["text"])
            if key and (key in t or t in key):
                s = float(ln["start"])
                return (s, s + float(d.get("hold", 0.5))), None
        return None, f"锚点文本在字幕里找不到"
    return None, "需要 anchor 或 start"


# ============================ 滤镜链 ============================
def _fit_fades(length: float, fi: float, fo: float) -> tuple[float, float]:
    """
    淡入 + 淡出不能吃满整段。
    实测踩过：head 段只有 1.5s，而淡入 1.0s + 交接淡出 0.5s = 1.5s
    → **整段都在渐变里**，没有满音量时刻（volumedetect 只有 -58dB，等于没听见）。
    → 保底留 20% 长度的满音量段。
    """
    total = fi + fo
    room = length * 0.8
    if total > room > 0:
        k = room / total
        return fi * k, fo * k
    return fi, fo


def _bgm_segment(label_in: str, label_out: str, off: float, length: float,
                 gain: float, fade_in: float, fade_out: float) -> str:
    """截取一段 BGM：定位 → 增益 → 首尾淡入淡出"""
    length = max(length, 0.05)
    fade_in, fade_out = _fit_fades(length, fade_in, fade_out)
    parts = [f"atrim=start={off:.3f}:end={off + length:.3f}",
             "asetpts=N/SR/TB",
             f"volume={gain}dB"]
    if fade_in > 0.01:
        parts.append(f"afade=t=in:st=0:d={min(fade_in, length):.3f}")
    if fade_out > 0.01:
        st = max(0.0, length - fade_out)
        parts.append(f"afade=t=out:st={st:.3f}:d={min(fade_out, length):.3f}")
    return f"{label_in}{','.join(parts)}{label_out}"


def build_filter(p: dict, pre_chain: str | None, total: float,
                 out_label: str = "aout") -> str:
    """
    生成 filter_complex 字符串。
      输入 0 = 视频（含口播），输入 1 = BGM 文件
      输出 [out_label] = 混好的完整音轨（**尚未** loudnorm）

    ⛔ 混音必须在 loudnorm 之前（见模块头说明），所以这里只到混音为止。
    """
    total = float(total)
    f = []
    # ① 口播（前置处理链原样复用）
    f.append(f"[0:a]{pre_chain}[vp]" if pre_chain else "[0:a]anull[vp]")

    if p["placement"] == "full":
        t_end = min(total, float(p["region"][1]))
        chain = [f"atrim=start=0:end={t_end:.3f}", "asetpts=N/SR/TB",
                 f"volume={p['gain']}dB"]
        if p["fade_out"] > 0:
            st = max(0.0, t_end - p["fade_out"])
            chain.append(f"afade=t=out:st={st:.3f}:d={min(p['fade_out'], t_end):.3f}")
        # 人声区间 → 额外压低（每段一个 volume 实例，用 timeline 的 enable）
        dl = db2lin(-p["duck"])
        for s, e in (p.get("duck_spans") or []):
            chain.append(f"volume=volume={dl}:enable='between(t,{s:.3f},{e:.3f})'")
        # 定点额外压低（「某句」那半秒）
        for d in p["dips"]:
            s, e = d["span"]
            chain.append(f"volume=volume={db2lin(-d['extra'])}:"
                         f"enable='between(t,{s:.3f},{e:.3f})'")
        f.append(f"[1:a]{','.join(chain)}[bgm0]")
        f.append(f"[vp][bgm0]amix=inputs=2:duration=first:normalize=0:"
                 f"dropout_transition=0[{out_label}]")
        return ";".join(f)

    # 头尾模式：需要几段就 split 几路
    segs = [k for k in ("head", "tail") if p.get(k)]
    if len(segs) == 2:
        f.append("[1:a]asplit=2[b0][b1]")
    else:
        f.append("[1:a]anull[b0]")

    labels, off = [], 0.0
    for i, k in enumerate(segs):
        s, e = p[k]
        length = e - s
        # head 段：开头淡入 + 交接到人声时淡出
        # tail 段：从人声结束处淡入 + 片尾淡出
        fi = p["fade_in"] if k == "head" else p["handoff"]
        fo = p["handoff"] if k == "head" else p["fade_out"]
        lab = f"[bg{i}]"
        f.append(_bgm_segment(f"[b{i}]", lab, off, length, p["gain"], fi, fo))
        if k == "tail" and s > 0:
            ms = int(round(s * 1000))
            # ⚠️ adelay 放在 afade 之后：这样 afade 的时间以片段自身为 0 起算
            f.append(f"{lab}adelay={ms}|{ms}{lab}")
        labels.append(lab)
        off += length          # 后一段接着前一段放，听感像"同一首在延续"

    f.append("".join(["[vp]"] + labels) +
             f"amix=inputs={len(labels) + 1}:duration=first:normalize=0:"
             f"dropout_transition=0[{out_label}]")
    return ";".join(f)


def describe(p: dict) -> list[str]:
    """给人看的计划摘要"""
    L = [f"曲目：{p['name']}  （{p['note']}）",
         f"音量：{p['gain']:+.1f} dB 相对口播"]
    if p["placement"] == "full":
        n = len(p.get("duck_spans") or [])
        L.append(f"位置：**全程垫底**，人声出现时自动压低 {p['duck']:.0f} dB"
                 + (f"（{n} 段包络）" if n else "（⚠️ 无时间码，未压低）"))
    else:
        seg = []
        if p["head"]:
            seg.append(f"开头 0~{p['head'][1]:.1f}s")
        if p["tail"]:
            seg.append(f"结尾 {p['tail'][0]:.1f}~{p['tail'][1]:.1f}s")
        L.append(f"位置：{'、'.join(seg)}（头尾无口播处）")
    if p["dips"]:
        L.append("定点压低：" + "、".join(
            f"{d['span'][0]:.1f}s 再压 {d['extra']:.0f}dB" for d in p["dips"]))
    L.append(f"淡入/淡出：{p['fade_in']:.1f}s / {p['fade_out']:.1f}s"
             f"（交接 {p['handoff']:.1f}s）")
    return L


# ============================ 自检 ============================
SELFTEST_DIR = os.path.join(os.environ.get("TEMP", "/tmp"), "bgm_selftest")


def _mk(d, name, text):
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, name), "w", encoding="utf-8") as f:
        f.write(text)


def selftest() -> int:
    ok = fail = 0
    base = SELFTEST_DIR
    # ⛔ 自检必须幂等：上一轮生成的音频会被当成曲库曲目，导致「空曲库」用例失败
    #    （实测踩过：跑到第二轮时 ③ 从 3 首变成 5 首）
    shutil.rmtree(base, ignore_errors=True)
    lib = os.path.join(base, "_资产", "bgm")
    proj = os.path.join(base, ".workbuddy")
    os.makedirs(proj, exist_ok=True)
    os.makedirs(lib, exist_ok=True)      # ① 就要验「项目级曲库被发现」，得先建出来

    def check(name, cond, extra=""):
        nonlocal ok, fail
        if cond:
            ok += 1
            print(f"  ✓ {name}")
        else:
            fail += 1
            print(f"  ✗ {name}  {extra}")

    print("=" * 68)
    print("① 曲库发现")
    print("=" * 68)
    check("项目根识别（含 .workbuddy）", project_root(os.path.join(base, "x")) == base,
          project_root(os.path.join(base, "x")))
    dirs = bgm_dirs(base)
    check("识别到项目级曲库", lib in dirs, str(dirs))

    print("\n" + "=" * 68)
    print("② 曲库为空 → 必须报错，且说清怎么办")
    print("=" * 68)
    try:
        plan({"style": "安静的钢琴"}, None, 60.0, dirs)
        check("空曲库应抛错", False, "没抛")
    except ValueError as e:
        check("空曲库抛 ValueError", "曲库是空的" in str(e), str(e)[:60])
        check("错误里含「怎么建曲库」指引", "怎么建曲库" in str(e) or "曲库是空的" in str(e))

    print("\n" + "=" * 68)
    print("③ 建曲库 → 风格筛")
    print("=" * 68)
    _mk(lib, "曲库.md", """# BGM 曲库

| 文件 | 风格 | 情绪 | 时长 | 适用 |
|---|---|---|---|---|
| 钢琴_安静_60s.mp3 | 钢琴 安静 治愈 | 平静 | 62s | 口播垫底 |
| 钢琴_温暖_45s.mp3 | 钢琴 温暖 | 柔和 | 47s | 亲子 |
| 弦乐_紧张_30s.mp3 | 弦乐 紧张 悬疑 | 紧绷 | 32s | 转折 |
""")
    for n in ("钢琴_安静_60s.mp3", "钢琴_温暖_45s.mp3", "弦乐_紧张_30s.mp3"):
        open(os.path.join(lib, n), "wb").close()

    tracks = scan(bgm_dirs(base))
    check("扫到 3 首", len(tracks) == 3, str(len(tracks)))
    check("索引生效（indexed=True）", all(t["indexed"] for t in tracks))

    ranked = match(tracks, "安静的钢琴")
    check("「安静的钢琴」首选 安静_60s",
          ranked and ranked[0][2]["name"] == "钢琴_安静_60s.mp3",
          ranked[0][2]["name"] if ranked else "-")
    check("命中词含「安静」「钢琴」",
          "安静" in ranked[0][1] and "钢琴" in ranked[0][1], str(ranked[0][1]))
    check("命中多者优先（弦乐得分更低）", ranked[0][0] > ranked[-1][0],
          f"{ranked[0][0]} vs {ranked[-1][0]}")
    ranked2 = match(tracks, "紧张")
    check("「紧张」筛到弦乐", ranked2[0][2]["name"] == "弦乐_紧张_30s.mp3",
          ranked2[0][2]["name"])
    check("无命中时最高分为 0", match(tracks, "手风琴布鲁斯")[0][0] == 0,
          str(match(tracks, "手风琴布鲁斯")[0][:2]))

    # ③b 真正可解码的音频（前面建的是 0 字节占位，只够验「扫描/匹配」）
    print("\n  · 生成真实测试音频（供 ⑦ 实跑混音）")
    FF0 = ffmpeg()
    ok_mp3 = True
    for n, freq, dur in (("钢琴_安静_60s.mp3", 440, 60),
                         ("钢琴_温暖_45s.mp3", 330, 45),
                         ("弦乐_紧张_30s.mp3", 220, 30)):
        r = run([FF0, "-hide_banner", "-loglevel", "error", "-y",
                 "-f", "lavfi",
                 "-i", f"sine=frequency={freq}:duration={dur}:sample_rate=44100",
                 "-af", "volume=0.25,aformat=channel_layouts=stereo",
                 "-c:a", "libmp3lame", "-b:a", "128k", os.path.join(lib, n)])
        ok_mp3 = ok_mp3 and r.returncode == 0
    check("测试用 mp3 生成成功", ok_mp3)

    print("\n" + "=" * 68)
    print("④ 定曲目")
    print("=" * 68)
    p, note = resolve({"file": "钢琴_温暖_45s.mp3"}, bgm_dirs(base))
    check("file 指定能找到", p and p.endswith("钢琴_温暖_45s.mp3"), str(note))
    p, note = resolve({"style": "治愈 钢琴"}, bgm_dirs(base))
    check("style 筛到（含 note）", p is not None and "命中" in note, note)
    p, note = resolve({"file": "不存在.mp3"}, bgm_dirs(base))
    check("指定文件不存在 → 返回 None", p is None and "找不到" in note, note)
    p, note = resolve({}, bgm_dirs(base))
    check("既无 file 也无 style → 报错", p is None and "二选一" in note, note)

    print("\n" + "=" * 68)
    print("⑤ 区间计划（head_tail）")
    print("=" * 68)
    lines = [{"start": 3.4, "end": 8.0, "text": "第一句"},
             {"start": 80.0, "end": 86.2, "text": "最后一句"}]
    pp = plan({"file": "钢琴_安静_60s.mp3"}, lines, 91.8, bgm_dirs(base))
    check("head = 0~3.4", pp["head"] == (0.0, 3.4), str(pp["head"]))
    check("tail = 86.2~91.8", pp["tail"] == (86.2, 91.8), str(pp["tail"]))
    check("placement = head_tail", pp["placement"] == "head_tail")

    pp2 = plan({"file": "钢琴_安静_60s.mp3", "head_s": 20.0, "tail_s": 85.0},
               lines, 91.8, bgm_dirs(base))
    check("head_s/tail_s 可覆盖", pp2["head"] == (0.0, 20.0), str(pp2["head"]))

    try:
        plan({"file": "钢琴_安静_60s.mp3"}, [{"start": 0.5, "end": 91.3, "text": "x"}],
             91.8, bgm_dirs(base))
        check("头尾太短应抛错", False, "没抛")
    except ValueError as e:
        check("头尾太短抛错并给替代方案",
              "full" in str(e) or "min_len" in str(e), str(e)[:70])

    pp3 = plan({"file": "钢琴_安静_60s.mp3", "placement": "full",
                "duck": 12}, lines, 91.8, bgm_dirs(base))
    check("full 模式 region = 全片", pp3["region"] == (0.0, 91.8))
    check("duck 默认 12", pp3["duck"] == 12.0)

    # ⭐ 位置是**参数**：中文/英文都认（用户 2026-09-24 要求可切换）
    for val, want in (("全程", "full"), ("全片", "full"), ("full", "full"),
                      ("头尾", "head_tail"), ("首尾", "head_tail"),
                      ("head_tail", "head_tail"), (None, "head_tail")):
        c = {"file": "钢琴_安静_60s.mp3"}
        if val is not None:
            c["placement"] = val
        got = plan(c, lines, 91.8, bgm_dirs(base))["placement"]
        check(f"placement「{val}」→ {want}", got == want, got)

    pp4 = plan({"file": "钢琴_安静_60s.mp3",
                "dips": [{"anchor": "最后一句", "extra": 6, "hold": 0.5}]},
               lines, 91.8, bgm_dirs(base))
    check("dips 按锚点定位", len(pp4["dips"]) == 1 and
          abs(pp4["dips"][0]["span"][0] - 80.0) < 0.01, str(pp4["dips"]))

    print("\n" + "=" * 68)
    print("⑥ 滤镜链（结构与关键参数）")
    print("=" * 68)
    ch = build_filter(pp, "highpass=f=80,arnndn=m=bd.rnnn,deesser", 91.8)
    check("头尾：两段 asplit", "asplit=2" in ch, ch[:60])
    check("头尾：amix inputs=3", "inputs=3" in ch, ch[-90:])
    check("amix normalize=0（否则音量被改）", "normalize=0" in ch)
    check("amix duration=first", "duration=first" in ch)
    check("tail 段有 adelay 定位", "adelay=" in ch)
    check("增益写成 dB", "volume=-24.0dB" in ch, ch)

    ch2 = build_filter(pp3, None, 91.8)
    check("full：用音量包络做压低，**不用** sidechaincompress",
          "sidechaincompress" not in ch2 and "enable='between(t," in ch2, ch2[:100])
    check("full：按人声区间生成 2 段包络",
          len(pp3.get("duck_spans") or []) == 2, str(pp3.get("duck_spans")))
    check("包络区间前后留 lead（人声起音前就退下去）",
          abs(pp3["duck_spans"][0][0] - (3.4 - 0.08)) < 0.002,
          str(pp3["duck_spans"][0]))
    check("包络数量与滤镜实例一致",
          ch2.count("enable='between(t,") == 2,
          str(ch2.count("enable='between(t,")))
    check("full：无前置链时用 anull", "[0:a]anull[vp]" in ch2)

    mg = _merge_spans([(0.0, 1.0), (1.2, 2.0), (10.0, 11.0)], gap=0.5, total=20.0)
    check("相邻区间合并（间隔 < gap）", mg == [(0.0, 2.0), (10.0, 11.0)], str(mg))
    mg2 = _merge_spans([(-1.0, 2.0), (19.0, 25.0)], gap=0.5, total=20.0)
    check("区间裁剪到 [0, total]", mg2 == [(0.0, 2.0), (19.0, 20.0)], str(mg2))
    mg3 = _merge_spans([], gap=0.5, total=20.0)
    check("空输入返回空", mg3 == [], str(mg3))

    pp5 = plan({"file": "钢琴_安静_60s.mp3", "placement": "full"},
               None, 91.8, bgm_dirs(base))
    check("无时间码时 duck_spans 为空（不崩，只警告）",
          pp5.get("duck_spans") == [], str(pp5.get("duck_spans")))

    seg = _bgm_segment("[x]", "[y]", 0.0, 1.5, -20.0, 1.0, 0.5)
    check("淡入+淡出占满整段时自动压缩（保底 20% 满音量）",
          "d=0.800" in seg and "d=0.400" in seg, seg)
    seg2 = _bgm_segment("[x]", "[y]", 0.0, 10.0, -20.0, 1.0, 1.0)
    check("长度充足时不改淡入淡出", "d=1.000" in seg2, seg2)

    print("\n" + "=" * 68)
    print("⑦ 真实混音（生成音频，用 ffmpeg 实跑）")
    print("=" * 68)
    FF = ffmpeg()
    vt = os.path.join(lib, "_测试口播.wav")
    bt = os.path.join(lib, "钢琴_安静_60s.mp3")
    # 造 10 秒"口播"：0~2s 静音 + 2~7s 说话 + 7~10s 静音
    p1 = run([FF, "-hide_banner", "-loglevel", "error", "-y",
              "-f", "lavfi", "-i", "sine=frequency=220:duration=10:sample_rate=48000",
              "-af", "volume=enable='lt(t,2)+gt(t,7)':volume=0,"
                     "aformat=channel_layouts=stereo",
              "-c:a", "pcm_s16le", vt])
    check("生成测试口播（含首尾静音）", os.path.isfile(vt) and p1.returncode == 0,
          (p1.stderr or "")[-120:])

    lines10 = [{"start": 2.0, "end": 7.0, "text": "中段说话"}]
    pl = plan({"file": "钢琴_安静_60s.mp3", "gain": -20, "min_len": 1.0,
               "fade_in": 0.5, "fade_out": 0.5, "handoff": 0.5},
              lines10, 10.0, bgm_dirs(base))
    check("头段 0~2.0 / 尾段 7.0~10.0",
          pl["head"] == (0.0, 2.0) and pl["tail"] == (7.0, 10.0),
          f'{pl["head"]} {pl["tail"]}')
    fc = build_filter(pl, None, 10.0)
    outw = os.path.join(lib, "_混音结果.wav")
    pr = run([FF, "-hide_banner", "-loglevel", "error", "-y",
              "-i", vt, "-stream_loop", "-1", "-i", bt,
              "-filter_complex", fc, "-map", "[aout]",
              "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", outw])
    check("ffmpeg 混音实跑成功", pr.returncode == 0 and os.path.isfile(outw),
          (pr.stderr or "")[-200:])

    if pr.returncode == 0:
        def band(path, s, t=0.6):
            """取一段的平均音量（dB）；数字静音记 -120 便于比较"""
            r = run([FF, "-hide_banner", "-ss", str(s), "-t", str(t), "-i", path,
                     "-af", "volumedetect", "-f", "null", "-"])
            m = re.search(r"mean_volume:\s*(-?[\d.]+)", r.stderr or "")
            return float(m.group(1)) if m else -120.0

        # ⭐ 等位对照：同一时间点上「纯口播」vs「混音后」。
        #    拿头部与中段互比是不严谨的（两处声源本来就不同）；
        #    只有同位对照才能查出 BGM 有没有**漏进人声段**。
        for tag, t, want_bgm in (("头段", 1.0, True),
                                 ("中段", 3.0, False),
                                 ("尾段", 8.0, True)):
            v, m = band(vt, t), band(outw, t)
            d = m - v
            if want_bgm:
                check(f"{tag}有 BGM（混音高出 ≥8dB）", d >= 8.0, f"Δ{d:+.1f}dB")
            else:
                check(f"{tag}无 BGM 泄漏（与纯口播几乎一致）", abs(d) <= 1.5,
                      f"Δ{d:+.1f}dB")

    # ⑦b 压低包络**真的压得动吗**（这是全篇最关键的一条）
    #     只测 BGM 链本身、不含口播 —— 否则口播在带通里的阻带泄漏会污染读数。
    envw = os.path.join(lib, "_包络验证.wav")
    dl = db2lin(-12)
    fc_env = (f"[0:a]atrim=start=0:end=10,asetpts=N/SR/TB,volume=-20dB,"
              f"volume=volume={dl}:enable='between(t,2,7)'[out]")
    pe = run([FF, "-hide_banner", "-loglevel", "error", "-y",
              "-i", bt, "-filter_complex", fc_env, "-map", "[out]",
              "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", envw])
    check("包络链实跑成功", pe.returncode == 0 and os.path.isfile(envw),
          (pe.stderr or "")[-160:])
    if pe.returncode == 0:
        def band2(path, s, t=0.8):
            r = run([FF, "-hide_banner", "-ss", str(s), "-t", str(t), "-i", path,
                     "-af", "highpass=f=80,lowpass=f=150,volumedetect",
                     "-f", "null", "-"])
            m = re.search(r"mean_volume:\s*(-?[\d.]+)", r.stderr or "")
            return float(m.group(1)) if m else -120.0

        a = band2(envw, 0.5)     # 包络区间之前（未压低）
        b = band2(envw, 3.0)     # 包络区间内（应压低 12dB）
        c = band2(envw, 8.5)     # 包络区间之后（应恢复）
        d = b - a
        check("压低 12dB 的包络**真的压了约 12dB**", -14.5 < d < -9.5,
              f"Δ{d:+.1f}dB（区间前 {a:.1f} / 区间内 {b:.1f}）")
        check("包络区间结束后恢复原音量", abs(c - a) < 2.0,
              f"恢复后 {c:.1f} vs 之前 {a:.1f}")

    print("\n" + "=" * 68)
    print(f"结果：通过 {ok} / 失败 {fail}")
    print("=" * 68)
    return 1 if fail else 0


# ============================ CLI ============================
def _dirs_from_args(a) -> list[str]:
    hints = [x for x in (a.md, a.videos_dir, a.dir) if x]
    return bgm_dirs(*hints) if hints else bgm_dirs(os.getcwd())


def _library_help(dirs: list[str]) -> str:
    return (
        "\n【怎么建曲库】\n"
        "  1. 建一个目录（推荐项目级，可跨系列复用）：\n"
        "       <项目根>/_资产/bgm/\n"
        "     单篇专属的也可以放在：\n"
        "       <某篇文案目录>/_素材/bgm/\n"
        f"  2. 把音乐文件（{'/'.join(e.lstrip('.') for e in AUDIO_EXTS)}）放进去\n"
        f"  3. 建 {INDEX_NAME} 标注风格，格式：\n\n"
        "       | 文件 | 风格 | 情绪 | 时长 | 适用 |\n"
        "       |---|---|---|---|---|\n"
        "       | 钢琴_安静_60s.mp3 | 钢琴 安静 治愈 | 平静 | 62s | 口播垫底 |\n\n"
        "     没有这个文件也能用，但风格只剩「文件名关键词」可匹配，准确度会低。\n"
        f"  当前已扫描目录：{('、'.join(dirs) if dirs else '（都不存在）')}\n"
        "  ⛔ 本工具**不联网下载音乐**（版权风险）——需要你提供。")


def main():
    ap = argparse.ArgumentParser(description="BGM 轨道（背景音乐混入）")
    ap.add_argument("--list", action="store_true", help="列曲库")
    ap.add_argument("--pick", metavar="风格", help="试一次风格筛选")
    ap.add_argument("--dir", help="指定文案/素材目录（用于推断曲库位置）")
    ap.add_argument("--md", help="文案 MD 路径（推断曲库用）")
    ap.add_argument("--videos-dir", help="素材目录（推断曲库用）")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return selftest()

    dirs = _dirs_from_args(a)
    if a.list:
        print("曲库目录：")
        print("  " + ("\n  ".join(dirs) if dirs else "（一个都不存在）"))
        tracks = scan(dirs)
        print(f"\n曲目（{len(tracks)} 首）：")
        for t in tracks:
            tag = "索引" if t["indexed"] else "文件名"
            print(f"  [{tag}] {t['name']}")
            print(f"          {t['text'][:70]}")
        if not tracks:
            print(_library_help(dirs))
        return 0

    if a.pick:
        tracks = scan(dirs)
        ranked = match(tracks, a.pick)
        print(f"风格「{a.pick}」匹配结果（{len(tracks)} 首候选）：")
        for score, hits, t in ranked[:8]:
            mark = "←" if score == ranked[0][0] and score > 0 else " "
            print(f" {mark} {score} 词命中 [{('、'.join(hits)) or '-'}]  {t['name']}")
        if not ranked or ranked[0][0] == 0:
            print("\n没有匹配的曲目。")
            print(_library_help(dirs))
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
