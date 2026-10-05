# -*- coding: utf-8 -*-
"""视频号文案自检（只读）——把 SOP 里「能跑脚本核的」一次跑完。

它核什么（都有明文硬指标）：
  【口播区】字数 / 句数 / 最长分句(≤16) / 拍摄提示数(≤6) / 台词行里有没有混进【】/ 超长行
  【上屏区】各上屏元素字数上限、锚点句能否在口播里逐字找到、挂句是否独占一行、标色词是否跨行
  【换算】字数 ÷ 4.3 = 预计时长（SOP 全篇唯一语速口径；⚠️ 落点表偏乐观 5~7%）

用法：
    PY="C:/Users/ZhuanZ/.workbuddy/binaries/python/versions/3.13.12/python.exe"
    "$PY" 工具脚本/video_script_check.py "…/视频号文案_00_先导_总纲.md"
    "$PY" 工具脚本/video_script_check.py <目录>        # 目录下所有 *.md（跳过以 _ 开头的系列级文件）

退出码：0 = 无 FAIL；1 = 有 FAIL（WARN 不影响退出码）。
"""
import argparse
import glob
import io
import os
import re
import sys
import unicodedata

sys.stdout.reconfigure(encoding="utf-8")

CJK = r"\u4e00-\u9fff"
WORD_RE = re.compile(rf"[{CJK}a-zA-Z0-9]")
TIP_RE = re.compile(r"^【")
INLINE_TIP_RE = re.compile(r"【")
# ⭐ 「结构标记」≠「拍摄提示」（2026-10-02 分开计数）——
#   【引流·可选】【合集·过渡】【系列·说明】【★金句】标的是**这几句的用途/身份**，不是**怎么念**，
#   不受"拍摄提示 ≤6 处"约束（那条约束的由来是"素人念得顺不顺"，见 SOP 922/811）。
STRUCT_TIP_RE = re.compile(r"^【(引流|合集|系列|★|☆)")
SENT_SPLIT = re.compile(r"[。！？]")
CLAUSE_SPLIT = re.compile(r"[，、；：]")

MAX_CLAUSE = 16      # 分句硬上限（3.0）
MAX_TIPS = 6         # 拍摄提示（方括号行）上限，**只数念法提示**
SPEED = 4.3          # 字/秒（全篇唯一口径）
# ⭐ 单条时长硬上限（2026-10-03 改版）：原 180 秒（3 分钟）→ **210 秒（3.5 分钟）**。
#   判据比"真片预计"（落点表偏乐观 5~7%，先 ×1.07 再比）→ 对应口播 ≈844 字含标点。
#   口径变更依据见 `_资产/视频号方案改版_v1（已确认）.md`。
MAX_SEC = 210.0

# 上屏元素：区块名关键词 → (显示名, 字数上限)
LIMITS = [
    ("开头钩子", "开头钩子", 16),
    ("强调句", "底部字幕(强调)", 20),
    ("金句大字卡", "金句大字卡", 16),
    ("浅底卡", "浅底卡", 30),
    ("封面", "封面大字", 16),
    ("录制提示", "录制提示", 999),   # 只列挂句，不设上限
]
# 这些区块的文字**不是锚点**（钩子/封面是片子外面的字；录制提示是给人看的）
NO_ANCHOR = {"开头钩子", "封面大字", "录制提示"}


def find_section(text: str, keyword: str):
    """按关键词找节标题（**编号任意**，与管道 `_section()`／`gen_prompter.py` 同口径）。

    2026-10-03：新 6 节模板的编号变成「一、口播文案」，旧写法写死「## 二、」会找不到。
    返回**完整标题行**（供 zone() 定位），找不到返回 None。
    """
    for line in text.split("\n"):
        s = line.strip()
        if re.match(r"^#{1,4}\s", s) and keyword in s:
            return s
    return None


def zone(text: str, head: str):
    """取出 head 开头的区块正文。

    结束判据（取先出现的那个）：
      · 一个独立成行的 `---`（口播区就是这么划的）
      · 下一个同级/更高级标题（`## ` 或 `# 【`）——上屏方案区用它收口，
        否则会把「五、怎么合成」里的说明文字也当成上屏数据扫进来。
    """
    i = text.find(head)
    if i < 0:
        return None
    out = []
    for line in text[i + len(head):].split("\n"):
        s = line.strip()
        if s == "---":
            break
        if out and (s.startswith("## ") or s.startswith("# 【")):
            break
        out.append(line)
    return "\n".join(out)


def visual_len(s: str) -> int:
    """视觉宽度近似：非空白字符全算（引号、标点也占位，折行按它估）。"""
    return len(re.sub(r"\s", "", s))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="文案 md 或目录")
    args = ap.parse_args()

    if os.path.isdir(args.target):
        files = sorted(f for f in glob.glob(os.path.join(args.target, "**", "*.md"), recursive=True)
                       if not os.path.basename(f).startswith("_"))
    else:
        files = [args.target]
    if not files:
        print("未找到 md")
        return 1

    bad = 0
    for path in files:
        fails, warns = [], []
        t = io.open(path, encoding="utf-8").read()

        # ── 口播区 ────────────────────────────────────────────
        sec_spoken = find_section(t, "口播文案")
        body = zone(t, sec_spoken) if sec_spoken else None
        if body is None:
            print(f"❌ {os.path.basename(path)}：找不到含「口播文案」的节标题")
            bad = 1
            continue
        raw_lines = [l.strip() for l in body.split("\n") if l.strip()]
        tips = [l for l in raw_lines if TIP_RE.match(l) and not STRUCT_TIP_RE.match(l)]
        structs = [l for l in raw_lines if STRUCT_TIP_RE.match(l)]
        # ⚠️ **结构标记行的正文是"要念的台词"**（2026-10-03 修）——
        #   原来用 `not TIP_RE.match(l)` 一刀切，把 `【引流·可选】更细的…` 这**整行**排除在台词之外。
        #   ⭐ **正确写法是"标记独占一行、台词另起一行"**（存量 6 条全都这么写）；
        #   写成**同一行**时会出两个错：
        #     ① `gen_prompter.extract_spoken()` **整行丢掉** → **提词器里没有这句 → 出镜者漏念**；
        #     ② 本脚本把整行排除在台词外 → **字数/时长漏算**。
        #   → 所以：**遇到行内写法直接报 FAIL**（逼它改），同时把标记剥掉后照常计入（数字先算对）。
        spoken = []
        for l in raw_lines:
            if STRUCT_TIP_RE.match(l):
                s = re.sub(r"^【[^】]*】\s*", "", l)
                if s.strip():
                    fails.append(
                        "结构标记写成了「标记＋台词」同一行（提词器会**整行丢掉**、出镜者漏念）："
                        f"{l[:22]}… —— 请把台词另起一行，标记独占一行")
                    spoken.append(s.strip())
            elif not TIP_RE.match(l):
                spoken.append(l)

        for l in spoken:
            if INLINE_TIP_RE.search(l):
                fails.append(f"台词行里混进了【】：{l[:24]}…（提词器会照念出来）")

        joined = "\n".join(spoken)
        chars = len(WORD_RE.findall(joined))          # 汉字+字母+数字（不含标点）
        # ⚠️ 口径修正（2026-10-03）：管道的逐字稿字数与 SOP 的 ÷4.3 语速口径
        #   **都是"含标点"**（实测同一稿：汉字 284 / 含标点 328）——
        #   原来按汉字算会把时长低估约 13%，用来卡"3 分钟上限"会漏判。
        chars_vis = sum(visual_len(l) for l in spoken)
        sents = [s for s in SENT_SPLIT.split(joined) if s.strip()]

        over_clause = []
        for l in spoken:
            for c in CLAUSE_SPLIT.split(l):
                c = c.strip()
                if c and len(WORD_RE.findall(c)) > MAX_CLAUSE:
                    over_clause.append((len(WORD_RE.findall(c)), c))
        long_lines = [(len(WORD_RE.findall(l)), l) for l in spoken if len(WORD_RE.findall(l)) > 30]

        # ── 代词体检（SOP 3.9「少用代词、直接称呼」；2026-10-02 自动化）──────
        #   铁律：指代家人要写**称呼**（孩子／妈妈），不写"他／她"。
        #   ⛔ 但有两种例外：① 别人的原话一字不动；② 转述"我当年说过的话"按当时口气。
        #   → 所以**只列清单、不自动判错**（自动判错会在这两处产生误报）。
        #   由来：05/06 顺稿时用户反馈「代词不知道指的是谁」，而这条 SOP 早就写了，
        #   漏在执行——**靠通读不如靠清单**。
        PRON = re.compile(r"(?<![其])他|她|它")
        IND = re.compile(r"这件事|那件事|这些|那些|这样|那样|这种|这两步|那两句")
        pr = [(i + 1, l) for i, l in enumerate(spoken) if PRON.search(l)]
        ind = [(i + 1, l) for i, l in enumerate(spoken) if IND.search(l)]

        # ── 电报腔体检（2026-10-02 立：用户两次提同一件事之后补的**工具化**）──────
        #   用户两次说同一句话：「提词器不够通顺／有些话上下连不上／（缺）副词」。
        #   ⛔ 根因不是"没写规则"——SOP 里写了（"句内用逗号，**句与句之间用口语连接词**"、
        #      "别写成每行一个短句、行末都落句号的电报腔"），**但只写在一条里、没有检查**，
        #      于是改完 05 又犯在 06 上。→ 判据必须能被脚本抓出来。
        #   判据：**连续 ≥3 行、每行 ≤12 字、行首 5 字内没有连接词 → 疑似电报腔**。
        #   ⚠️ 两类**要排除**（它们"看起来碎"但必须碎）：
        #      ① **上屏句**——它们**必须各自独占一行**（挤在一行会带上半句）；
        #      ② 刻意的节奏句（如"加课，加题，加安排。"）——它本身就是设计。
        LINKW = ("后来", "可", "可是", "但", "但是", "不过", "所以", "因为", "要是", "如果",
                 "其实", "而且", "而", "也", "就", "才", "于是", "反而", "尤其", "然后",
                 "接着", "再说", "既", "又", "终于", "毕竟", "难怪", "原来", "现在",
                 "那阵子", "这时候", "我呢", "因此", "还有", "只是", "甚至", "虽然",
                 "哪怕", "至少", "结果", "最后", "首先", "其次", "同时")
        sec_screen = find_section(t, "上屏方案")
        scr_blk = (zone(t, sec_screen) if sec_screen else None) or ""
        on_screen = []
        for ln in scr_blk.split("\n"):
            s2 = ln.strip()
            target = s2.split("挂在", 1)[1] if "挂在" in s2 else s2
            if s2.startswith("- ") and "挂在" not in s2:
                continue
            for a in re.findall(r"「([^」]+)」", target):
                on_screen.append(a.rstrip("。？！"))

        def is_onscreen(s: str) -> bool:
            return any(a and (a in s or s.startswith(a)) for a in on_screen)

        # ⚠️ **只报"数字"，不逐条报**（2026-10-02 实测：逐条判会大量误报）——
        #   三类**刻意的短句**长得跟电报腔一样，机器分不开：
        #   ① **对话**（"他说，想呀。／我说，那明天能去吗？"）
        #   ② **列举的节奏**（"去图书馆，去公园。"／"有时候是头疼。／有时候早上就不起床。"）
        #   ③ **照念台词**（"我们先不争要不要上。／你觉得它有什么用？"）
        #   → 所以给一个**可对比的比例**，由人judge；判据写在 SOP 与下面这行提示里。
        pure_short = [l for l in spoken
                      if len(WORD_RE.findall(l)) <= 12 and not is_onscreen(l)]
        ratio = len(pure_short) / max(len(spoken), 1)
        print(f"短句行占比：{len(pure_short)}/{len(spoken)}（{ratio:.0%}）"
              + ("　⚠️ 偏碎——逐段看：连续 3 行以上都 ≤12 字、又**不是对话/列举**，就该合并、补连接词"
                 if ratio > 0.45 else ""))

        if len(tips) > MAX_TIPS:
            fails.append(f"拍摄提示 {len(tips)} 处 > {MAX_TIPS} 处")
        if over_clause:
            fails.append("分句超 {0} 字：{1}".format(
                MAX_CLAUSE, "；".join(f"{n}字「{c}」" for n, c in over_clause)))
        if long_lines:
            warns.append("台词行超 30 字（念着容易断气）：" +
                         "；".join(f"{n}字" for n, _ in long_lines))

        sec = chars_vis / SPEED
        print(f"\n=== {os.path.basename(path)} ===")
        print(f"口播：{chars_vis} 字（含标点；汉字 {chars}）/ {len(sents)} 句 / {len(spoken)} 行　"
              f"拍摄提示 {len(tips)} 处"
              + (f"（另有结构标记 {len(structs)} 处，不计）" if structs else ""))
        print(f"时长：≈ {sec:.0f} 秒 ({int(sec//60)}:{sec%60:04.1f})"
              f"　⚠️ 落点表偏乐观，真片预计 {sec*1.05:.0f}~{sec*1.07:.0f} 秒"
              f"（{sec*1.07/60:.1f} 分）")
        if sec * 1.07 > MAX_SEC:
            fails.append(f"真片预计 {sec*1.07:.0f} 秒 > {MAX_SEC:.0f} 秒（{MAX_SEC/60:.1f} 分钟上限）"
                         f"—— 口播要压到 {MAX_SEC/1.07*SPEED:.0f} 字以内（含标点）")
        if pr:
            print(f"代词体检：他/她/它 {len(pr)} 处 —— 逐条问一句「这是谁」"
                  f"（别人的原话／当年转述可照留）")
            for i, l in pr[:12]:
                print(f"    台词第 {i} 行：{l[:26]}")
            if len(pr) > 12:
                print(f"    …另有 {len(pr) - 12} 处")
        if ind:
            print(f"指示代词 {len(ind)} 处（这些／这样／这件事…）—— 确认指代对象在本篇里点过名")

        # ── 上屏区 ────────────────────────────────────────────
        scr = zone(t, sec_screen) if sec_screen else None
        if scr is None:
            warns.append("找不到含「上屏方案」的节标题")
        else:
            cur, curlim = None, 99
            for line in scr.split("\n"):
                s = line.strip()
                # ⚠️ `>` 开头的是**说明行，不是数据**（2026-10-03 修）——
                #   实测：在 `### 封面` 后写一段 `> ⚠️ … **BGM 未定** …`，
                #   其中 `**BGM 未定**` 被当成**封面大字**，报"没带标点"。
                #   SOP 本来就要求"说明／示例／警告一律写到「四、视频合成方案」"，
                #   这里补一道兜底，与硬坑 42 对「全片标色／浅底卡」的处理同口径。
                if s.startswith(">"):
                    continue
                for key, name, lim in LIMITS:
                    if s.startswith("###") and key in s:
                        cur, curlim = name, lim
                        break
                if s.startswith("###") and "序号条" in s:
                    cur, curlim = "序号条", 16

                anchors = re.findall(r"「([^」]+)」", s)
                # ── 锚点只从「条目行」里取（2026-10-02 修精度）────────────────
                #   实测（05/06 顺稿时）三类误报，全是**说明文字被当成挂句**：
                #     ① `> 底部字幕要用「多停」。`        ← 在讲**字段名**，不是台词
                #     ② `…先看「五、怎么合成」第 5 条…`     ← 在**引用章节**
                #     ③ `卡面「…」→ 挂在「正句」`          ← **卡面**被当成了挂句（真挂句在"挂在"后面）
                #   规则：只认含 `→`／`挂句`／`挂在`／行首编号 的行；
                #   且含「挂在」时**只校验"挂在"之后**的那个「」。
                if not re.search(r"→|挂句|挂在|大字|^\s*\d+\.", s):
                    continue
                if "挂在" in s:
                    after = re.findall(r"「([^」]+)」", s.split("挂在", 1)[1])
                    if after:
                        anchors = after
                # 钩子/封面用的是 `**大字**`；⭐ 封面文字**必须加粗**——
                # 管道 parse_cover 只认 `**…**` 或「」，写成纯文本 `大字：XXX` 会**解析不到封面**
                # （2026-10-01 实测踩过：reference/md_authoring_guide.md 的写法与代码不一致）
                if cur in ("开头钩子", "封面大字"):
                    for b in re.findall(r"\*\*([^*]+)\*\*", s):
                        b = b.strip()
                        # ⚠️ 跳过**说明行**里的加粗（2026-10-02）：钩子段常带一行
                        #    `**0~2 秒 ＝ 静止封面卡（带钩子大字）／2 秒起 ＝ 正片，画面干净**`
                        #    —— 那是**给后期看的时间说明**，不是大字文案，被当成大字会误报"29 字 > 16 字"。
                        if "秒" in b or "＝" in b:
                            continue
                        if visual_len(b) > curlim:
                            fails.append(f"[{cur}] {visual_len(b)} 字 > {curlim} 字：{b}")
                        if not re.search(r"[，。？！；、]", b):
                            warns.append(f"[{cur}] 没带标点（大字自动折行会断在意想不到处）：{b}")
                if not anchors:
                    continue
                is_hook_anchor = ("挂在这句" in s) or ("挂句" in s) or ("挂在" in s)
                for a in anchors:
                    a_clean = a.strip().rstrip("。？！")
                    if is_hook_anchor:
                        if a not in joined:
                            fails.append(f"[{cur}] 挂句不在口播里：{a[:24]}")
                        continue
                    if cur in NO_ANCHOR:
                        vl = visual_len(a)
                        if vl > curlim:
                            fails.append(f"[{cur}] {vl} 字 > {curlim} 字：{a}")
                        continue
                    # 锚点必须在口播里逐字存在
                    hit_line = next((l for l in spoken if a in l), None)
                    if hit_line is None:
                        if a_clean and any(a_clean in l for l in spoken):
                            warns.append(f"锚点差标点：{a[:20]}（能匹配但未逐字，建议照抄整句）")
                        elif cur == "金句大字卡":
                            # 大字卡的**卡面允许是提炼句**（可补主语、可把两句并成一句）；
                            # 它在片上的**时间码由下面那行「挂在这句」决定**，不是卡面本身
                            # （2026-10-02 修：06 主卡"治得了我的慌，治不了他的累"拆在口播两行里，
                            #  卡面逐字找不到是正常的，不该报 ❌）
                            warns.append(f"[{cur}] 卡面不在口播里（允许——时间码看「挂在这句」）："
                                         f"{a[:24]}")
                        else:
                            fails.append(f"[{cur or '?'}] 锚点在口播里找不到：{a[:24]}")
                        continue
                    # 上屏文本：越接近整行越好（字幕取的是"命中的那一行原文"）
                    if hit_line != a:
                        warns.append(f"[{cur}] 上屏句非整行 → 字幕会显示整行："
                                     f"「{a[:16]}…」 → 实际「{hit_line[:16]}…」")
                    vl = visual_len(a)
                    if vl > curlim:
                        fails.append(f"[{cur}] 上屏 {vl} 字 > {curlim} 字：{a[:20]}")

        # ── 封面：文字必须加粗（管道 parse_cover 只认 `**…**` 或「」）────
        if scr and "### 封面" in scr:
            seg = scr[scr.find("### 封面"):]
            j = seg.find("\n###")
            cover_blk = seg[:j] if j >= 0 else seg
            # ⚠️ 同上：说明行（`>` 开头）**不是封面文字**——但这里要**报出来**，
            #    因为封面区写说明是最容易发生的一处（2026-10-03 实测踩到）。
            if any(ln.strip().startswith(">") for ln in cover_blk.split("\n")):
                warns.append("「### 封面」区块里混进了 `>` 说明行——"
                             "说明请移到「四、视频合成方案」（本次已按非封面文字跳过）")
                cover_blk = "\n".join(ln for ln in cover_blk.split("\n")
                                      if not ln.strip().startswith(">"))
            if not re.search(r"\*\*.+?\*\*", cover_blk) and not re.findall(r"「[^」]+」", cover_blk):
                warns.append("封面文字既没加粗也没用「」——管道解析不到封面"
                             "（实测：写成纯文本 `大字：XXX` → 封面 0）")

        # ── 全片标色 ──────────────────────────────────────────
        color_zone = None
        if scr:
            i = scr.find("### 全片标色")
            if i >= 0:
                seg = scr[i:]
                j = seg.find("\n###")
                color_zone = seg[:j] if j >= 0 else seg
        if color_zone:
            words = re.findall(r"[\"“]([^\"”]+)[\"”]", color_zone)
            for w in words:
                w = w.strip()
                if not w:
                    continue
                if w not in joined:
                    fails.append(f"标色词不在口播里：{w}")
                elif not any(w in l for l in spoken):
                    fails.append(f"标色词跨行（会静默丢失着色）：{w}")

        # ── 视频描述 ≤100 字（官方上限 1000，我们只用到 100）────────────
        i = t.find("**视频描述")
        if i >= 0:
            seg = t[i:].split("\n")[1:]
            desc = ""
            for ln in seg:
                s = ln.strip()
                if s.startswith(">"):
                    desc = s.lstrip("> ").strip()
                    break
                if s and not s.startswith(">"):
                    break
            if desc:
                n = visual_len(desc)
                mark = "✅" if n <= 100 else "❌"
                print(f"描述：{n} 字 / 100 {mark}")
                if n > 100:
                    fails.append(f"视频描述 {n} 字 > 100 字")
            else:
                warns.append("没找到「视频描述」正文（以 > 开头的那行）")

        # ── 短标题：字数 ≤16 ＋ **符号白名单**（微信官方口径，2026-10-01）────
        #    官方原文：「标题包含特殊字符，符号仅支持书名号、引号、冒号、加号、问号、
        #              百分号、摄氏度，逗号可用空格代替」
        #    → 除白名单外的标点/符号一律不合格；**逗号要换成空格**（不是删掉，
        #      删掉会让短语粘连）。顿号、感叹号、句号、括号、破折号、省略号、分号都不行。
        TITLE_OK = set("《》〈〉「」『』“”‘’\"'：:＋+？?％%℃°")
        # ⚠️ 找「短标题」这一行的**标题行**：不能直接 find("短标题")——
        #    04 的引言里就出现过「描述」和「短标题」两个字段，会先命中引言。
        #    判据：不以 ">" 开头（引言都是 blockquote），且带 "≤16"／"16 字"这类说明。
        all_lines = t.split("\n")
        start = None
        for idx, ln in enumerate(all_lines):
            if ln.lstrip().startswith(">"):
                continue
            if "短标题" in ln and ("≤16" in ln or "16 字" in ln or "16字" in ln):
                start = idx
                break
        if start is None:                       # 06 的字段名写的是「视频号标题」
            for idx, ln in enumerate(all_lines):
                if ln.lstrip().startswith(">"):
                    continue
                if "视频号标题" in ln:
                    start = idx
                    break
        if start is not None:
            seg = all_lines[start + 1:]
            checked = 0
            for ln in seg[:12]:
                s = ln.strip()
                if s.startswith(("- **", "**", ">")) or not s:
                    if checked:
                        break
                    continue
                m = re.match(r"^([①②③④⑤]|\d+[.、])\s*(.+)$", s)
                if not m:
                    if checked:
                        break
                    continue
                body = m.group(2)     # ⚠️ group(1) 是行首编号，标题在 group(2)
                body = re.split(r"（\s*\d+\s*字", body)[0]     # 去掉「（12 字）」
                body = body.split("←")[0]                     # 去掉行尾备注
                body = body.strip().strip("*").strip()
                if not body:
                    continue
                checked += 1
                n = visual_len(body)
                bad_chars = [(c, unicodedata.category(c))
                             for c in body
                             if unicodedata.category(c)[0] in ("P", "S")
                             and c not in TITLE_OK]
                ok_n = "✅" if n <= 16 else "❌"
                ok_c = "✅" if not bad_chars else "❌"
                print(f"短标题 {checked}：{n} 字/16 {ok_n}｜符号 {ok_c}  {body}")
                if n > 16:
                    fails.append(f"短标题「{body}」{n} 字 > 16 字")
                if bad_chars:
                    uniq = "".join(dict.fromkeys(c for c, _ in bad_chars))
                    fails.append(
                        f"短标题「{body}」含微信不支持的符号：{uniq}"
                        f"（逗号请换成空格，其余需改写/删除）")
                if body != body.strip() or "  " in body:
                    warns.append(f"短标题「{body}」有连续/首尾空格")
            if not checked:
                warns.append("没解析到短标题候选（行首应为 ①②③）")

        # ── 朋友圈转发文案：自足 ＋ 系列串连（2026-10-02 立）──────────────────
        #   用户实读反馈：「有些读不懂」（例：02 的"有些话，是说完好几年才回过味来"），
        #                  「而且好像每篇之间也没有联系」。
        #   两条硬规则：
        #     ① **首行不许悬置指代**——以"有些话／那句话／这一句"开头，读者不知道指什么；
        #     ② **系列条要串**——中间那段回收上一条的过渡语（用词与口播咬合）。
        #       ⚠️ **单篇不走这条**（用户：「如果是单篇，那就重点写本篇最吸引人的」）。
        SNIP_HEAD = re.compile(
            r"^(有些话|那些话|那句话|这句话|这一句|那句|这句|有些事|有些时候|从小到大)")
        lines_all = t.split("\n")
        p = None
        for i, ln in enumerate(lines_all):
            if "朋友圈转发文案" in ln and ln.strip().endswith("："):
                p = i
                break
        if p is not None:
            got, in_code, started = [], False, False
            for ln in lines_all[p + 1:p + 28]:
                s = ln.strip()
                if s.startswith("```"):
                    if in_code:
                        break
                    in_code = started = True
                    continue
                if in_code:
                    got.append(s)
                    continue
                if s.startswith(">"):                 # 手机方案的写法：引用块
                    v = s.lstrip(">").strip()
                    if v.startswith(("- ", "⚠️", "⭐", "ℹ️", "注意")):
                        break
                    got.append(v)
                    started = True
                    continue
                if s and started:
                    break
            f_rows = [x for x in got if x]
            if not f_rows:
                warns.append("没解析到朋友圈转发文案正文")
            else:
                f_txt = " ".join(f_rows)
                n = visual_len(f_txt)
                if n > 160:
                    fails.append(f"朋友圈转发文案 {n} 字，太长（一屏内 ≈120 以内）")
                elif n > 120:
                    warns.append(f"朋友圈转发文案 {n} 字，手机上一屏可能要划（建议 ≤120）")
                print(f"朋友圈文案：{n} 字（≤120 最好）｜{f_rows[0][:20]}…")
                if SNIP_HEAD.match(f_rows[0]):
                    fails.append(
                        "朋友圈首行用了悬置指代（" + f_rows[0][:12] +
                        "…）——读者不知道指什么；换成一件能独立看懂的具体事")
                is_series = bool(re.match(r"^视频号文案_\d+", os.path.basename(path))) or \
                    bool(re.match(r"^\d+_", os.path.basename(os.path.dirname(path))))
                if is_series:
                    if not re.search(r"(第\s*\d+\s*条|先导条)", f_txt):
                        warns.append("系列条的朋友圈文案缺「系列坐标」"
                                     "（如《××》第 2 条 · 共 6 条）")
                    m = re.search(r"第\s*(\d+)\s*条", f_txt)
                    if m and int(m.group(1)) > 1 and "上一条" not in f_txt:
                        warns.append("系列条的中间那段建议回收上一条的过渡语"
                                     "（用词与口播咬合），两条才串得起来")

        for f in fails:
            print("  ❌ " + f)
        for w in warns:
            print("  ⚠️  " + w)
        if not fails:
            print("  ✅ 硬指标全部通过")
        bad = bad or (1 if fails else 0)

    print()
    return bad


if __name__ == "__main__":
    sys.exit(main())
