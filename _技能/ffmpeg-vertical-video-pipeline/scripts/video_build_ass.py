r"""
ASS 字幕生成器 —— 把「口播文案 + 时间码 + 剪辑决策」编译成 ASS 字幕文件

为什么用 ASS 而不是 SRT：
  ASS 支持行内逐字改色/加粗/缩放（{\c&H..&} {\b1} {\fscx110}），
  能直接实现文案里"关键指标用暖色加粗"这类要求——SRT 做不到。

为什么必须自动折行：
  CJK 字符是满宽的。16 个汉字 × 104px = 1664px，而竖屏画面只有 1080px 宽，
  不折行就会**两侧被裁掉**（实测踩过）。故所有文本都按视觉宽度自动折行。

用法：
    from video_build_ass import build_ass
    build_ass(spec, out_path)

自检：
    python video_build_ass.py --selftest
"""
from __future__ import annotations

import os
import sys
import io

# 原地改编码，不新建 TextIOWrapper —— 否则被别的模块 import 时会双重包装，
# 把已关闭的 buffer 再包一层，报 "I/O operation on closed file"（踩过）
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


# ---------- ASS 颜色： &HAABBGGRR（BGR 顺序！与常见的 RRGGBB 相反） ----------
def ass_color(hex_rgb: str, alpha: int = 0) -> str:
    r"""'#D97706' -> '&H000677D9'"""
    h = hex_rgb.lstrip("#")
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H{alpha:02X}{b}{g}{r}".upper()


# 文案里的"暖橙/暖棕系"（MD 要求）——莫兰迪低饱和，忌高饱和原色
WARM = "#C2703C"
WARM_DEEP = "#A8551F"
WHITE = "#FFFFFF"

# ---------- 版式常量（针对 1080x1920 竖屏） ----------
PLAY_RES_X, PLAY_RES_Y = 1080, 1920
FONT = "Microsoft YaHei"
MARGIN_LR = 70

# ⭐ 视频号 UI 遮挡区（实测+检索估算，单位 px，画面 1080x1920）
#    ⚠️ 这些数字是**估算**——正式发布前建议用真机看一眼确认（`--safe-check` 会按它报警）。
SAFE = {
    "top": 180,      # 顶部：作者信息 / 关注按钮
    "bottom": 360,   # 底部：标题文案 + 评论区入口（**最容易压住字幕**）
    "right": 110,    # 右侧：点赞/评论/转发/收藏按钮（竖排在右下）
    "left": 60,
}

# 样式参数集中定义，方便整体系调
#   margin_lr: 左右安全边距 —— 底部字幕要留够，避免行尾伸进右侧按钮区
#   anim: ASS 覆盖标签，写在每条 Dialogue 开头。零额外渲染成本（libass 内建）
STYLE_DEF = {
    # ⚠️ margin_v 从 300 提到 460：实测 300 时字幕正好压在底部标题/评论区入口上
    # ⚠️ margin_lr=110 是"右侧按钮区"逼出来的：可用宽 860px。
    #    字号定 68 是为了让**最常见的一行 12 字**（12×68=816）刚好放得下、不折行。
    "字幕":   dict(size=68,  color=WHITE,     align=2, margin_v=460, margin_lr=110, bold=False,
                   outline=3, shadow=1,
                   anim=r"\fad(180,180)"),
    # 强调字幕：仍在底部，但明显比常规字幕醒目。
    # ⭐ 「全程字幕 + 金句突出」那种版本用的就是它——比另起一张居中大卡克制，
    #    也不会打断"全程有字幕"的阅读节奏。
    "强调":   dict(size=82,  color=WHITE,     align=2, margin_v=460, margin_lr=110, bold=True,
                   outline=4, shadow=1,
                   anim=r"\fad(180,180)"),
    # 序号条：顶部居中（实测确认不在右侧按钮区）
    "序号条": dict(size=76,  color=WHITE,     align=8, margin_v=260, margin_lr=70, bold=True,
                   outline=4, shadow=1,
                   anim=r"\fad(140,140)"),
    # 金句卡：画面正中（也在朋友圈 1:1 裁切的安全区内）；
    # 淡入 + 极轻微推近（1.00→1.06，500ms），比硬切显得"有设计"
    "金句":   dict(size=100, color=WHITE,     align=5, margin_v=0,   margin_lr=70, bold=True,
                   outline=5, shadow=2,
                   anim=r"\fad(260,260)\t(0,500,\fscx106\fscy106)"),

    # ---- 浅底文字卡（`BorderStyle=3` 用 Background 盒画底）----
    # 「台词小卡 / 话术卡 / 小字卡 / 祝愿卡」都用它：
    #   浅米底 + 深字、位置在**字幕上方**（不与字幕打架）、**不加动画**
    #   字号靠 item 级 `size` 微调（MD 常写"比字幕大一号 / 比金句卡小很多"）
    # ⚠️ BorderStyle=3 时，`outline` 的角色变成"底板内边距"（padding），不是描边粗细
    "小卡":   dict(size=76,  color="#2B2B2B", align=2, margin_v=620, margin_lr=110,
                   bold=False, outline=18, shadow=0, border_style=3,
                   back_color="#F7F2E8", back_alpha=0x14,
                   anim=""),

    # 引用小字：**更小 + 半透明 + 无动画**（03 篇的「引用标记」）
    #   alpha=0x70 ≈ 70% 透明；暖棕、不加粗，是"轻轻提一下"的语气
    "引用":   dict(size=58,  color=WARM_DEEP, align=2, margin_v=620, margin_lr=110,
                   bold=False, outline=2, shadow=0, alpha=0x70,
                   anim=""),
}

# ⭐ 元素 key → 该 key 下的**默认样式**（每条可用 item["style"] 换整套样式）
#   提成常量，三处（安全区检查 / 渲染 / 自检）共用 ——
#   否则加一种元素就要改三处，迟早漏一处（同类教训：hook 能力加了、解析忘了接）
#     cards：浅底文字卡（台词小卡 / 话术卡 / 小字卡 / 祝愿卡）
ELEMENT_KEYS = (
    ("subs", "字幕"),
    ("seq", "序号条"),
    ("cards", "小卡"),
    ("punch", "金句"),
)

# item 上可直接给的样式覆盖（编译成 ASS 行内标签）
# ⚠️ 只支持**不改定位**的属性。想换位置（居中/靠上）请用 "style" 切换整套样式——
#    用行内标签改 align 要靠 \pos 绝对定位，容易在中英混排时错位，得不偿失。
_OVERRIDE_TAGS = (
    ("color",         lambda v: f"\\c{ass_color(str(v))}"),
    ("outline_color", lambda v: f"\\3c{ass_color(str(v))}"),
    ("size",          lambda v: f"\\fs{int(v)}"),
    ("outline",       lambda v: f"\\bord{int(v)}"),
    ("shadow",        lambda v: f"\\shad{int(v)}"),
    ("spacing",       lambda v: f"\\fsp{float(v):g}"),
)


def _override_tags(item: dict, base: dict) -> str:
    """把 item 的样式覆盖编译成一段 ASS 行内标签（无覆盖时返回空串）"""
    tags = []
    for k, fn in _OVERRIDE_TAGS:
        if item.get(k) is not None:
            tags.append(fn(item[k]))
    if item.get("bold") is not None:
        tags.append("\\b1" if item["bold"] else "\\b0")
    if item.get("scale"):
        sc = int(float(item["scale"]) * 100)
        tags.append(f"\\fscx{sc}\\fscy{sc}")
    if item.get("alpha") is not None:
        # 支持两种写法：0~1 的比例，或 ASS 原生的 0~255
        a = float(item["alpha"])
        av = int(round(a * 255)) if a <= 1 else int(a)
        tags.append(f"\\alpha&H{max(0, min(255, av)):02X}&")
    return "{" + "".join(tags) + "}" if tags else ""


def _ts(sec: float) -> str:
    """秒 -> ASS 时间戳 H:MM:SS.cc"""
    if sec < 0:
        sec = 0.0
    cs = int(round(sec * 100))
    h, rem = divmod(cs, 360000)
    m, rem = divmod(rem, 6000)
    s, c = divmod(rem, 100)
    return f"{h}:{m:02d}:{s:02d}.{c:02d}"


def _esc(text: str) -> str:
    r"""ASS 文本转义：花括号是标签定界符必须转义；换行用 \N"""
    return (text.replace("\\", "\\\\")
                .replace("{", "\\{")
                .replace("}", "\\}")
                .replace("\n", "\\N"))


# ---------- 视觉宽度估算与自动折行 ----------
BREAK_AFTER = "，。！？；：、,.!?;:"
BREAK_BEFORE = "）】》」』]}"


def text_width(text: str, fontsize: float) -> float:
    """估算渲染宽度：CJK/全角 ≈ 1 字宽，ASCII ≈ 0.5 字宽"""
    w = 0.0
    for ch in text:
        o = ord(ch)
        if o < 0x2000:                      # ASCII / 拉丁
            w += 0.5
        else:                               # CJK / 全角标点
            w += 1.0
    return w * fontsize


def wrap_cjk(text: str, fontsize: float, max_width: float) -> str:
    """
    贪心折行，优先在标点后断开，其次标点前，最后硬断。
    返回用 '\\n' 连接的文本（交由 _esc 转成 ASS 的 \\N）。
    """
    text = text.strip()
    if not text:
        return text
    if text_width(text, fontsize) <= max_width:
        return text

    lines, cur = [], ""
    for ch in text:
        cur += ch
        if text_width(cur, fontsize) > max_width:
            # 超宽了，回溯找断点
            cut = -1
            for i in range(len(cur) - 1, 0, -1):
                if cur[i - 1] in BREAK_AFTER:
                    cut = i
                    break
            if cut <= 0:
                for i in range(len(cur) - 1, 0, -1):
                    if cur[i] in BREAK_BEFORE:
                        cut = i
                        break
            if cut <= 0:
                # 兜底硬断：取**中点**而不是塞满一行 ——
                # 否则第一行塞满、末行只剩一两个字（实测很难看）。
                # （中文没有词间空格，硬断必然切开某处，但均衡断读起来舒服得多）
                cut = max(1, len(cur) // 2)
            lines.append(cur[:cut])
            cur = cur[cut:]
    if cur:
        lines.append(cur)
    return "\n".join(x.strip() for x in lines if x.strip())


def render_line(text: str, marks: list[dict] | None = None) -> str:
    r"""
    按 marks 插行内标签。
    marks: [{"word":"装的","color":"#C2703C","bold":True,"scale":1.1}]
    匹配不到的 mark 静默忽略（方便一套标色规则复用到多篇）
    """
    if not marks:
        return _esc(text)

    spans = []
    for m in marks:
        w = m.get("word", "")
        if not w:
            continue
        idx = text.find(w)
        if idx < 0:
            continue
        spans.append((idx, idx + len(w), m))
    if not spans:
        return _esc(text)

    spans.sort(key=lambda x: (x[0], -(x[1] - x[0])))
    picked, last_end = [], -1
    for a, b, m in spans:
        if a >= last_end:
            picked.append((a, b, m))
            last_end = b

    out, cursor = [], 0
    for a, b, m in picked:
        out.append(_esc(text[cursor:a]))
        tag = ""
        if m.get("color"):
            tag += f"\\c{ass_color(m['color'])}"
        if m.get("bold"):
            tag += "\\b1"
        sc = m.get("scale")
        if sc and abs(sc - 1.0) > 1e-6:
            tag += f"\\fscx{int(sc*100)}\\fscy{int(sc*100)}"
        if tag:
            out.append("{" + tag + "}")
        out.append(_esc(text[a:b]))
        out.append("{\\r}")               # 复位，避免影响后续
        cursor = b
    out.append(_esc(text[cursor:]))
    return "".join(out)


def _style_line(name: str) -> str:
    r"""
    生成一行 ASS Style。

    支持的可选键（`STYLE_DEF` 里按样式给）：
      · `alpha`         主色（文字）透明度，0=不透明、255=全透明
      · `border_style`  1=描边+阴影（默认）／**3=在文字后面画一个底板**
      · `back_color` / `back_alpha`  BorderStyle=3 时的**底板颜色**

    ⛔ **BorderStyle=3 的底板颜色实际取自 `OutlineColour`，不是 `BackColour`**
      —— 实测踩过：把底板色写进 `BackColour` 时，渲染出来是一块**深灰底板**
      （因为 OutlineColour 仍是默认近黑色），配上深色字几乎看不清。
      所以这里在 BorderStyle=3 时把底板色**改写到 OutlineColour**。
    ⚠️ 此时 `outline` 的语义是「底板内边距」（padding），不是描边粗细。
    """
    s = STYLE_DEF[name]
    lr = s.get("margin_lr", MARGIN_LR)
    primary = ass_color(s["color"], int(s.get("alpha", 0)))
    bs = int(s.get("border_style", 1))
    if bs == 3:
        # 底板色 → OutlineColour（见上方说明）
        outline_c = ass_color(s.get("back_color", "#F7F2E8"),
                              int(s.get("back_alpha", 0x14)))
        back_c = "&H00000000"
    else:
        outline_c = ass_color(s.get("outline_color", "#1A1A1A"),
                              int(s.get("outline_alpha", 0)))
        back_c = ass_color(s.get("back_color", "#000000"),
                           int(s.get("back_alpha", 0x80)))
    return (
        f"Style: {name},{FONT},{s['size']},{primary},&H000000FF,"
        f"{outline_c},{back_c},"
        f"{-1 if s['bold'] else 0},0,0,0,100,100,0,0,"
        f"{bs},{s['outline']},{s['shadow']},"
        f"{s['align']},{lr},{lr},{s['margin_v']},134"
    )


def safe_check(spec: dict) -> list[str]:
    """
    检查各元素是否落在**视频号 UI 遮挡区**内，返回问题清单（空 = 全通过）。

    ⚠️ 遮挡区数字是估算的（见 SAFE），报出来的问题**值得当真**，
       但最终建议真机发一条"仅自己可见"确认一次。
    """
    issues = []
    rx, ry = spec.get("play_res", [PLAY_RES_X, PLAY_RES_Y])
    for key, style in ELEMENT_KEYS:
        for item in spec.get(key, []):
            st = item.get("style") or style
            sd = STYLE_DEF.get(st)
            if not sd:
                continue
            size = int(item.get("size") or sd["size"])
            mv = sd["margin_v"]
            an = sd["align"]
            tag = f"[{st}]「{str(item.get('text', ''))[:14]}」"
            # 近似的文字盒（按 1.4 倍行高、单行估算；多行只会更靠中间，更安全）
            h = size * 1.4
            if an in (1, 2, 3):                     # 底部对齐
                bottom = ry - mv
                top = bottom - h
                if bottom > ry - SAFE["bottom"]:
                    issues.append(f"{tag} 底边 {bottom:.0f}px 落在底部遮挡区"
                                  f"（应 < {ry - SAFE['bottom']}）→ 会被标题/评论区入口压住")
            elif an in (7, 8, 9):                   # 顶部对齐
                if mv < SAFE["top"]:
                    issues.append(f"{tag} 顶边 {mv:.0f}px 落在顶部遮挡区"
                                  f"（应 > {SAFE['top']}）")
            # 居中类（4/5/6）：垂直方向安全；只需看行宽是否伸进右侧按钮区
            lr = sd.get("margin_lr", MARGIN_LR)
            if an in (2, 5, 8):                     # 水平居中
                half = (rx - 2 * lr) / 2
                if rx / 2 + half > rx - SAFE["right"] and h > 0 and an == 2:
                    issues.append(f"{tag} 行宽可能伸进右侧按钮区"
                                  f"（可用宽 {rx - 2 * lr:.0f}px，右界 {rx / 2 + half:.0f}px"
                                  f" > {rx - SAFE['right']}）→ 调小字号或加大 margin_lr")
    return issues


def build_ass(spec: dict, out_path: str, wrap: bool = True) -> str:
    """
    spec = {
      "play_res": [1080,1920],                                            # 可选
      "subs":  [{"start":1.2,"end":4.5,"text":"...","marks":[...]}],      # 全程字幕（底部）
      "seq":   [{"start":20,"end":22,"text":"① 多久了"}],                 # 序号条（上部）
      "punch": [{"start":60,"end":64,"text":"检查没查出来，不等于孩子在装",
                 "marks":[{"word":"不等于孩子在装","color":"#C2703C","bold":True}]}],
    }

    ⭐ 任意一条都可做**样式覆盖**：
      "style": "强调"|"金句"|"序号条"|"字幕"   → 换整套样式（含位置）
      "size": 78 / "color": "#C2703C" / "bold": true / "scale": 1.2 / "outline": 5
                                              → 只改单项（保持原位）
    """
    rx, ry = spec.get("play_res", [PLAY_RES_X, PLAY_RES_Y])
    max_w = rx - 2 * MARGIN_LR

    L = ["[Script Info]", "ScriptType: v4.00+",
         f"PlayResX: {rx}", f"PlayResY: {ry}",
         "WrapStyle: 0", "ScaledBorderAndShadow: yes", "YCbCr Matrix: TV.709", ""]
    L += ["[V4+ Styles]",
          "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
          "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
          "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
          "Alignment, MarginL, MarginR, MarginV, Encoding"]
    # ⭐ 样式行**按 STYLE_DEF 动态生成**（不再写死名单）——
    #    避免"加了新样式却忘了加这一行"（实测踩过同类坑：hook 能力加了、解析忘了接）
    for nm in STYLE_DEF:
        L.append(_style_line(nm))
    L += ["", "[Events]",
          "Format: Layer, Start, End, Style, Name, MarginL, MarginR, "
          "MarginV, Effect, Text"]

    # anim=False 可整片关闭动画；单条也可用 item["anim"] 覆盖（None = 该条不动画）
    # item 级覆盖：`style` 换整套样式；`size`/`color`/`bold`/`scale`/`outline` 等改单项
    use_anim = spec.get("anim", True)
    n = 0
    for key, style in ELEMENT_KEYS:
        for item in spec.get(key, []):
            st = item.get("style") or style
            if st not in STYLE_DEF:
                st = style
            sd = STYLE_DEF[st]
            fs = int(item.get("size") or sd["size"])
            mw = rx - 2 * sd.get("margin_lr", MARGIN_LR)   # 折行按**样式自己的**可用宽算
            default_anim = sd.get("anim") if use_anim else None
            default_tag = "{" + default_anim + "}" if default_anim else ""
            txt = item["text"]
            if wrap:
                txt = wrap_cjk(txt, fs, mw)
            tag = item.get("anim", default_tag) or ""
            extra = _override_tags(item, sd)
            L.append(f"Dialogue: 0,{_ts(item['start'])},{_ts(item['end'])},"
                     f"{st},,0,0,0,,{tag}{extra}{render_line(txt, item.get('marks'))}")
            n += 1

    with open(out_path, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(L) + "\n")      # 带 BOM，libass 处理中文更稳
    return out_path


# ---------------- 自检 ----------------
def _selftest():
    spec = {
        "subs": [
            {"start": 0.0, "end": 3.2, "text": "那阵子我儿子老喊肚子疼。"},
            {"start": 3.4, "end": 7.0, "text": "我儿子，会不会是装的。",
             "marks": [{"word": "装的", "color": WARM, "bold": True, "scale": 1.12}]},
            {"start": 7.2, "end": 11.5, "text": "那点力气，本来该用来帮孩子的",
             "marks": [{"word": "帮孩子", "color": WARM, "bold": True}]},
            {"start": 11.5, "end": 15.0,
             "text": "这条故意放很长用来验证自动折行不会把文字挤出画面之外去"},
        ],
        "seq": [
            {"start": 20.0, "end": 21.8, "text": "① 多久了"},
            {"start": 21.8, "end": 23.6, "text": "② 影响多大"},
            {"start": 23.6, "end": 25.6, "text": "③ 有没有危险情况"},
        ],
        "punch": [
            {"start": 60.0, "end": 64.0, "text": "检查没查出来，不等于孩子在装",
             "marks": [{"word": "不等于孩子在装", "color": WARM_DEEP, "bold": True}]},
        ],
    }
    out = os.path.join(os.environ.get("TEMP", "."), "ffmpeg_verify", "selftest.ass")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    build_ass(spec, out)
    print(f"已生成：{out}\n")

    # 宽度自检：有没有哪一行超宽（**按各样式自己的可用宽**）
    print("=" * 70)
    print("折行结果与宽度自检")
    print("=" * 70)
    for key, style in ELEMENT_KEYS:
        sd = STYLE_DEF[style]
        fs = sd["size"]
        avail = PLAY_RES_X - 2 * sd.get("margin_lr", MARGIN_LR)
        for item in spec.get(key, []):
            wrapped = wrap_cjk(item["text"], fs, avail)
            for ln in wrapped.split("\n"):
                w = text_width(ln, fs)
                flag = "OK " if w <= avail else "超宽!"
                print(f"  [{style}] {flag} {w:7.0f}px / {avail}px  {ln}")

    # ⭐ 安全区自检：会不会被视频号 UI 压住
    print()
    print("=" * 70)
    print(f"安全区自检（顶部 {SAFE['top']} / 底部 {SAFE['bottom']} / 右侧 {SAFE['right']}）")
    print("=" * 70)
    for k, v in (("字幕", f"底部对齐，底边 y={PLAY_RES_Y - STYLE_DEF['字幕']['margin_v']}"
                  f"（遮挡区从 y={PLAY_RES_Y - SAFE['bottom']} 开始）"),
                 ("序号条", f"顶部对齐，顶边 y={STYLE_DEF['序号条']['margin_v']}"),
                 ("金句", "正中（也在朋友圈 1:1 裁切安全区内）")):
        print(f"  {k}：{v}")
    issues = safe_check(spec)
    if issues:
        print("\n  ⚠️ 发现问题：")
        for i in issues:
            print(f"    · {i}")
    else:
        print("\n  ✅ 全部落在安全区内")
    print()
    print("=" * 70)
    print("ASS 文件内容")
    print("=" * 70)
    print(open(out, encoding="utf-8-sig").read())
    print(f"颜色校验：{WARM} -> {ass_color(WARM)}   {WARM_DEEP} -> {ass_color(WARM_DEEP)}")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    elif "--safe-check" in sys.argv:
        import json
        i = sys.argv.index("--safe-check")
        p = sys.argv[i + 1] if len(sys.argv) > i + 1 else None
        if not p:
            print("用法：video_build_ass.py --safe-check <剪辑单.json>")
            sys.exit(1)
        sp = json.load(open(p, encoding="utf-8-sig"))
        res = safe_check(sp)
        if res:
            print("⚠️ 有元素可能被视频号 UI 压住：")
            for x in res:
                print(f"  · {x}")
            sys.exit(1)
        print("✅ 全部落在安全区内")
    else:
        print(__doc__)
