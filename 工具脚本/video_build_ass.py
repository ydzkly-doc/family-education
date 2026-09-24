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

# 样式参数集中定义，方便整体系调
STYLE_DEF = {
    "字幕":   dict(size=62,  color=WHITE,     align=2, margin_v=300, bold=False,
                   outline=3, shadow=1),
    "序号条": dict(size=76,  color=WHITE,     align=8, margin_v=260, bold=True,
                   outline=4, shadow=1),
    "金句":   dict(size=100, color=WHITE,     align=5, margin_v=0,   bold=True,
                   outline=5, shadow=2),
}


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
                cut = len(cur) - 1          # 硬断
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
    s = STYLE_DEF[name]
    return (
        f"Style: {name},{FONT},{s['size']},{ass_color(s['color'])},&H000000FF,"
        f"{ass_color('#1A1A1A')},&H80000000,"
        f"{-1 if s['bold'] else 0},0,0,0,100,100,0,0,1,{s['outline']},{s['shadow']},"
        f"{s['align']},{MARGIN_LR},{MARGIN_LR},{s['margin_v']},134"
    )


def build_ass(spec: dict, out_path: str, wrap: bool = True) -> str:
    """
    spec = {
      "play_res": [1080,1920],                                            # 可选
      "subs":  [{"start":1.2,"end":4.5,"text":"...","marks":[...]}],      # 全程字幕（底部）
      "seq":   [{"start":20,"end":22,"text":"① 多久了"}],                 # 序号条（上部）
      "punch": [{"start":60,"end":64,"text":"检查没查出来，不等于孩子在装",
                 "marks":[{"word":"不等于孩子在装","color":"#C2703C","bold":True}]}],
    }
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
    for nm in ("字幕", "序号条", "金句"):
        L.append(_style_line(nm))
    L += ["", "[Events]",
          "Format: Layer, Start, End, Style, Name, MarginL, MarginR, "
          "MarginV, Effect, Text"]

    n = 0
    for key, style in (("subs", "字幕"), ("seq", "序号条"), ("punch", "金句")):
        fs = STYLE_DEF[style]["size"]
        for item in spec.get(key, []):
            txt = item["text"]
            if wrap:
                txt = wrap_cjk(txt, fs, max_w)
            L.append(f"Dialogue: 0,{_ts(item['start'])},{_ts(item['end'])},"
                     f"{style},,0,0,0,,{render_line(txt, item.get('marks'))}")
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

    # 宽度自检：有没有哪一行超宽
    print("=" * 70)
    print("折行结果与宽度自检（画布宽 1080，可用宽 %d）" % (PLAY_RES_X - 2 * MARGIN_LR))
    print("=" * 70)
    for key, style in (("subs", "字幕"), ("seq", "序号条"), ("punch", "金句")):
        fs = STYLE_DEF[style]["size"]
        for item in spec.get(key, []):
            wrapped = wrap_cjk(item["text"], fs, PLAY_RES_X - 2 * MARGIN_LR)
            for ln in wrapped.split("\n"):
                w = text_width(ln, fs)
                flag = "OK " if w <= PLAY_RES_X - 2 * MARGIN_LR else "超宽!"
                print(f"  [{style}] {flag} {w:7.0f}px  {ln}")
    print()
    print("=" * 70)
    print("ASS 文件内容")
    print("=" * 70)
    print(open(out, encoding="utf-8-sig").read())
    print(f"颜色校验：{WARM} -> {ass_color(WARM)}   {WARM_DEEP} -> {ass_color(WARM_DEEP)}")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        print(__doc__)
