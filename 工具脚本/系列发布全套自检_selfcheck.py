# -*- coding: utf-8 -*-
"""公众号系列发布前全套自检（第9步）· 通用版

在任意系列的成果根目录（含 发布包_第X篇_*/ 的目录）下运行：
    python 工具脚本/系列发布全套自检_selfcheck.py

自动完成 9 项检查：
  1 发布包数量与篇号连续（自动读取期望篇数）
  2 三件套齐全（正文html + 01字段 + 封面；02 操作指南已取消）
  3 标题三处逐字一致（正文大标题 = 01字段表【标题】，标点归一后比对）
  4 文末来源声明在位（"非原文摘录" + 自定义关键词）
  5 无动作指令 / 无绝对化承诺
  6 结构规范（零 table/div/img/data-*，section 配平）
  7 wx_html_fix --check 必须"合格 N / N"
  8 合并预览页（_预览/ 独立目录，篇数正确）
  9 源正文 data-* 零残留（预览污染隔离）

可选参数：
    --source "扶鹰教育-王金海课程"   指定来源声明关键词（默认该值）
    --dir  <路径>                    指定成果根目录（默认当前目录）
    --legacy                         旧系列巡检模式：放行历史约定差异
                                     （02 为 .md / 早期包无 01·02 / 来源口径用旧写法），
                                     只报结构、污染、标题不一致等真问题
退出码：0 全通过 / 1 有未通过项
"""
import re, glob, os, subprocess, sys, argparse

def norm(s: str) -> str:
    """标题/文本归一化：去掉标点、引号（含中英弯直）、书名号、空白与连接符号。

    用于"正文大标题（多行拼接后无标点）"与"字段表标题（一行含标点）"的逐字比对，
    避免因分行为标点位置不同而产生的误报。
    """
    return re.sub(r'[，,：:。、；;！!？?…\u201c\u201d"\u300c\u300d《》（）()\[\]【】\s\-—·・\'‘’“”]', '', s)


# 兼容旧调用名
norm = norm
BAD_ACT = ["点在看", "点赞", "求关注", "转发、", "分享给", "扫码关注"]
BAD_ABS = ["一定能", "保证能", "必然", "彻底根治", "百分之百"]
# 常见误报豁免：叙事句里描述自己/他人点赞（非呼吁读者）时不算动作指令
# 常见误报豁免：叙事句里描述自己/他人点赞（非呼吁读者）时不算动作指令。
# 注意：替换必须"长词优先"，否则"百分之一"会先破坏"百分之百"的匹配边界。
ACT_EXEMPT = [
    "点赞越多", "点赞一条", "点赞了", "点赞过", "点赞数", "给我点赞",
    "分享给我", "分享给他", "分享给我听",
    "分享给你", "分享给你们", "分享给大家",  # 作者自述"我把这套分享给你"，非呼吁转发
]
ABS_EXEMPT = [
    "父母改变百分之一、孩子可能改变百分之百",  # 方法论表述，非对读者的绝对化承诺
    "改变百分之一", "改变百分之百",
    "百分之九十九",
    "不是四步话术的必然保证",  # 否定绝对效果，属于风险限定而非效果承诺
]
# 长词优先排序，避免短词先替换破坏长词边界
ACT_EXEMPT = sorted(ACT_EXEMPT, key=len, reverse=True)
ABS_EXEMPT = sorted(ABS_EXEMPT, key=len, reverse=True)


def head_title(html: str) -> str:
    """抽取正文顶部大标题（兼容多种历史写法）。

    判据（按出现顺序扫描 <p>...>文本</p>）：
      居中 且（字号 ≥20px，或未写字号但 display:block + 加粗 —— 早期系列写法）
    命中的连续若干行拼接为标题。坐标小字（≤13px）、金句块（17px）、
    陪伴卡（14px）会被阈值过滤；进入标题块后遇到小字号/非居中行即停。
    """
    out = []
    for m in re.finditer(r'<p\b[^>]*style="([^"]*)"[^>]*>([^<]+)</p>', html):
        style, text = m.group(1), m.group(2).strip()
        if not text:
            continue
        s = style.replace(" ", "")
        fs = re.search(r"font-size:\s*(\d+)px", style)
        size = int(fs.group(1)) if fs else 0
        centered = "text-align:center" in s
        is_title = centered and (size >= 20 or (fs is None and "display:block" in s and "bold" in s))
        if is_title:
            out.append(text)
            if len(out) >= 3:
                break
        elif out:
            if 0 < size <= 16 or (len(out) >= 2 and not centered):
                break
    if out:
        return "".join(out)
    return "".join(re.findall(r'display:block;">([^<]+)</p>', html))

ap = argparse.ArgumentParser()
ap.add_argument("--source", default="扶鹰教育-王金海课程", help="来源声明关键词")
ap.add_argument("--dir", default=".", help="成果根目录")
ap.add_argument("--legacy", action="store_true",
                help="旧系列巡检模式：放行历史约定差异，只看真问题")
args = ap.parse_args()
LEGACY = args.legacy

BASE = os.path.abspath(args.dir)
# 找工具脚本目录：向上搜索 工具脚本/
TOOLS = None
cur = BASE
for _ in range(4):
    cand = os.path.join(cur, "工具脚本")
    if os.path.isdir(cand):
        TOOLS = cand
        break
    cur = os.path.dirname(cur)

ok_all = True


def p(flag, msg):
    global ok_all
    if not flag:
        ok_all = False
    print(("  ✅ " if flag else "  ❌ ") + msg)


pkgs = sorted(glob.glob(os.path.join(BASE, "发布包_*")))
nums = sorted(int(m.group(1)) for d in pkgs if (m := re.search(r"第(\d+)篇", os.path.basename(d))))
N = len(pkgs)
series = os.path.basename(os.path.dirname(BASE)) or BASE


# ── 内容目录解析（兼容新旧两种发布包结构）────────────────────────────
# 新结构（2026-09-15 起）:  发布包_第X篇/长图文发布包/{正文,01,封面}
#                          发布包_第X篇/卡片发布包/{01,02,系列码_短名_第XX篇_卡片_NN_角色_vNN}
# 旧结构（历史）:          发布包_第X篇/{正文,01,封面}
def content_dir(pkg_dir, kind="长图文发布包"):
    """若存在对应子目录则用之，否则回退包根。kind 可为 '长图文发布包' / '卡片发布包'。"""
    sub = os.path.join(pkg_dir, kind)
    return sub if os.path.isdir(sub) else pkg_dir


def has_card_kit(pkg_dir):
    """是否含卡片发布包（含即需检查卡片交付物）"""
    return os.path.isdir(os.path.join(pkg_dir, "卡片发布包"))

print("=" * 62)
print(f"《{series}》发布前全套自检 · 共 {N} 个发布包")
print("=" * 62)

print(f"\n【1】发布包数量与篇号连续")
p(N > 0, f"找到 {N} 个发布包")
p(nums == list(range(1, N + 1)) if N else False, f"篇号 = {nums}（应连续 1..{N}）")

print("\n【2】三件套齐全（正文.html + 01字段.txt + 封面.jpg）")
# 2026-09-10 起：发布包标准 = 三件套，不再生成 02 操作指南。
#   严格模式：02 若意外出现只提示（不算失败），因为新规范已取消。
#   既有系列：历史带的 02_*.txt / .md 属历史产物，放行不报错。
for d in pkgs:
    cd = content_dir(d)
    fs = os.listdir(cd)
    h = [f for f in fs if f.startswith("正文_") and f.endswith(".html")]
    a = [f for f in fs if f.startswith("01_")]
    b = [f for f in fs if f.startswith("02_")]
    c = [f for f in fs if f.startswith("封面_第") and f.endswith(".jpg")]
    msg = (f"{os.path.basename(d)}：正文{len(h)} / 01:{len(a)} / 封面:{len(c)}"
           + (f" / 02:{len(b)}（历史）" if b else ""))
    if LEGACY:
        # 既有系列：正文必须有；01/02/封面缺失属历史约定，只提示不计失败
        ok = len(h) == 1
        note = []
        if not a: note.append("无 01 字段表")
        if not c: note.append("无封面")
        if note:
            print(f"  ℹ️  {msg}  ← 历史差异：{'、'.join(note)}")
            continue
    else:
        # 严格模式（新系列）：三件套齐全
        ok = len(h) == 1 and len(a) == 1 and len(c) == 1
        if b:
            # 02 操作指南已停止生成新篇，但存量一律保留（2026-09-10 用户明确）
            msg += "  ← 提示：02 指南已停生成新篇（存量保留，不影响通过）"
    p(ok, msg)

print("\n【2c】目录结构状态（提示项，不计失败）")
# 策略「逐篇随做」：做某篇卡片时顺手迁为新结构；未迁移的旧结构照常可用。
_new = [d for d in pkgs if os.path.isdir(os.path.join(d, "长图文发布包"))]
_old = [d for d in pkgs if not os.path.isdir(os.path.join(d, "长图文发布包"))]
print(f"  ℹ️  新结构 {len(_new)} 篇 / 旧结构 {len(_old)} 篇")
if _old:
    print(f"      旧结构（做卡片时顺手迁移即可，不影响自检）：{'、'.join(os.path.basename(d) for d in _old[:8])}"
          + ("…" if len(_old) > 8 else ""))
# 异常：有卡片发布包却没迁长图文（说明迁移漏了）
_bad_mig = [d for d in pkgs if has_card_kit(d) and not os.path.isdir(os.path.join(d, "长图文发布包"))]
for d in _bad_mig:
    p(False, f"{os.path.basename(d)}：有卡片发布包但未建长图文发布包 ← 迁移不完整")

print("\n【2b】卡片发布包（存在则检查；01字段 + 02正文 + 素材库全局唯一命名卡图）")
_cards = [d for d in pkgs if has_card_kit(d)]
if not _cards:
    print("  ℹ️  本系列暂无卡片发布包（卡片文章为可选增量）")
_asset_codes = set()
_all_card_names = []
_new_card_name_re = re.compile(
    r"^(?P<code>[A-Z][A-Z0-9]{3,11})_(?P<short>[^_]{2,16})_第(?P<part>\d{2})篇_"
    r"卡片_(?P<card>\d{2})_(?P<role>封面|内容|收尾)_v(?P<version>\d{2})\.jpg$"
)
for d in _cards:
    ck = os.path.join(d, "卡片发布包")
    fs = os.listdir(ck)
    _m = re.search(r"第(\d+)篇", os.path.basename(d))
    expected_part = int(_m.group(1)) if _m else None
    a2 = [f for f in fs if f.startswith("01_")]
    t2 = [f for f in fs if f.startswith("02_") and f.endswith(".txt")]
    # 先收集所有可能的卡图；旧命名仅在 --legacy 模式放行。
    g2 = sorted(f for f in fs
                if f.endswith(".jpg") and re.search(r"(^|_)卡片_\d\d_", f))
    # 体积与比例检查
    oversize = []
    for f in g2:
        fp = os.path.join(ck, f)
        kb = os.path.getsize(fp) / 1024
        if kb > 100:
            oversize.append(f"{f} {kb:.1f}KB")
    msg = (f"{os.path.basename(d)}：01字段{len(a2)} / 02正文{len(t2)} / 卡片{len(g2)}"
           + (f" ← 超100KB：{'、'.join(oversize)}" if oversize else ""))
    ok = len(a2) == 1 and len(t2) == 1 and 1 <= len(g2) <= 5 and not oversize
    if not LEGACY and len(g2) > 5:
        msg += " ← 卡片数超 5 张上限"
    # 新命名不能依赖本地目录：系列资产码 + 中文短名 + 篇号 + 卡序 + 角色 + 版本。
    parsed = []
    bad_names = []
    for f in g2:
        m2 = _new_card_name_re.match(f)
        if not m2:
            bad_names.append(f)
            continue
        parsed.append((f, m2))
        _asset_codes.add(m2.group("code"))
        _all_card_names.append(f)
        if expected_part is not None and int(m2.group("part")) != expected_part:
            ok = False
            msg += f" ← 文件篇号与发布包不一致：{f}"
    if bad_names and not LEGACY:
        ok = False
        msg += " ← 未采用素材库全局唯一命名：" + "、".join(bad_names[:3])
    if parsed:
        seq = [int(m.group("card")) for _, m in parsed]
        roles = [m.group("role") for _, m in parsed]
        if seq != list(range(1, len(seq) + 1)):
            ok = False
            msg += f" ← 卡序不连续：{seq}"
        if roles[0] != "封面" or roles[-1] != "收尾" or any(r != "内容" for r in roles[1:-1]):
            ok = False
            msg += " ← 卡位角色应为封面/内容…/收尾"
    p(ok, msg)

if not LEGACY and len(_asset_codes) > 1:
    p(False, f"同一系列出现多个素材资产码：{sorted(_asset_codes)}")
if not LEGACY and len(_all_card_names) != len(set(_all_card_names)):
    dup = sorted({n for n in _all_card_names if _all_card_names.count(n) > 1})
    p(False, "全系列卡图 basename 重复：" + "、".join(dup[:5]))

print("\n【3】标题三处逐字一致（正文大标题 = 01字段表【标题】）")
for d in pkgs:
    cd = content_dir(d)
    hfs = glob.glob(os.path.join(cd, "正文_*.html"))
    tfs = glob.glob(os.path.join(cd, "01_*.txt"))
    if not hfs:
        p(False, f"{os.path.basename(d)}：缺正文")
        continue
    if not tfs:
        if LEGACY:
            print(f"  ℹ️  {os.path.basename(d)}：历史差异（无 01 字段表，无法比对标题）")
            continue
        p(False, f"{os.path.basename(d)}：缺 01 字段表")
        continue
    head = head_title(open(hfs[0], encoding="utf-8").read())
    m = re.search(r"【标题】[^\n]*\n([^\n]+)", open(tfs[0], encoding="utf-8").read())
    ti = m.group(1).strip() if m else ""
    if not ti and LEGACY:
        print(f"  ℹ️  {os.path.basename(d)}：历史差异（01 字段表未用【标题】结构化格式）")
        continue
    same = norm(head) == norm(ti) and bool(ti)
    if not same and LEGACY and ti:
        # 旧系列容忍"分词位移"：正文分两行排版时标点会落在行首/行尾，
        # 去标点后若两边互为子串（即仅差断句位置），视为一致
        a, b = norm(head), norm(ti)
        same = bool(a) and (a in b or b in a)
        if same:
            print(f"  ℹ️  {os.path.basename(d)}：标题分词位置差异（正文分行所致），内容一致｜{ti}")
    p(same, f"{os.path.basename(d)}｜{ti}")

print("\n【4】文末来源声明在位")
src_norm = norm(args.source)
for d in pkgs:
    hf = glob.glob(os.path.join(content_dir(d), "正文_*.html"))[0]
    t = open(hf, encoding="utf-8").read()
    has_src = src_norm in norm(t)
    if LEGACY:
        # 旧系列来源写法各异，分三类，任一成立即通过：
        #   ① 课程类     → "扶鹰教育·王金海…非课程原文/非原文摘录"
        #   ② 读书笔记类 → "本文为读书笔记，观点整理自《书名》…非原文摘录"
        #   ③ 原创真实经历类 → "本文为作者真实经历原创分享…模糊化处理/转载请联系授权"
        has_origin = any(k in t for k in ("扶鹰", "整理自", "观点整理自", "观点整理", "读书笔记", "参考", "真实经历"))
        has_decl = any(k in t for k in ("版权", "非原文", "非课程", "非原著", "模糊化", "真实经历", "注明出处"))
        p(has_origin and has_decl, f"{os.path.basename(d)}｜含来源声明块")
    else:
        # ⭐ 2026-09-19 修正：严格分支原先只认"非原文摘录"三类，
        #   导致**「原创真实经历」类系列**（如《手机危机处理》，声明为
        #   "本文为作者真实经历原创分享…模糊化处理"）**永远无法通过自检**——
        #   因为这类文章本就不是"整理自他人原文"，不存在"非原文摘录"的说法。
        #   → 按内容类型分三支，任一成立即通过（与 LEGACY 分支的分类口径一致）。
        has_non_excerpt = any(k in t for k in ("非原文摘录", "非课程原文摘录", "非原著摘录"))
        # 原创真实经历类：须同时有"真实经历"与"模糊化/授权/不构成专业建议"之类的责任声明
        has_original_real = ("真实经历" in t) and any(
            k in t for k in ("模糊化", "转载请联系授权", "不构成专业建议", "注明出处"))
        p(has_non_excerpt or has_original_real,
          f"{os.path.basename(d)}｜{args.source}")

print("\n【5】无动作指令 / 无绝对化承诺")
for d in pkgs:
    t = open(glob.glob(os.path.join(content_dir(d), "正文_*.html"))[0], encoding="utf-8").read()
    # 只扫正文可见文字，排除 <script>/<style> 块，避免把导航脚本里的词当正文
    body = re.sub(r"<(script|style)\b.*?</\1>", "", t, flags=re.S | re.I)
    visible = re.sub(r"<[^>]+>", "", body)
    # 先剔除"叙事豁免"片段（如"点赞越多，我凉得越快"是描述，不是呼吁读者）
    scan = visible
    for ex in ACT_EXEMPT + ABS_EXEMPT:
        scan = scan.replace(ex, "")
    hit = [w for w in BAD_ACT + BAD_ABS if w in scan]
    p(not hit, f"{os.path.basename(d)}" + (f" ← {hit}" if hit else ""))

print("\n【6】结构规范（零 table/div/img/data-*，section 配平）")
for d in pkgs:
    t = open(glob.glob(os.path.join(content_dir(d), "正文_*.html"))[0], encoding="utf-8").read()
    so, sc = len(re.findall(r"<section[ >]", t)), len(re.findall(r"</section>", t))
    po, pc = len(re.findall(r"<p[ >]", t)), len(re.findall(r"</p>", t))
    bad = []
    for tag, pat in [("table", r"<table[ >]"), ("div", r"<div[ >]"), ("img", r"<img[ >]"),
                     ("h1-4", r"<h[1-4][ >]"), ("ul/li", r"<[uo]l[ >]|<li[ >]")]:
        n = len(re.findall(pat, t))
        if n:
            bad.append(f"{tag}={n}")
    nd = len(re.findall(r"\sdata-[a-zA-Z0-9_-]+=", t))
    if nd:
        bad.append(f"data-*={nd}")
    if so != sc:
        bad.append(f"section {so}/{sc}")
    if po != pc:
        bad.append(f"p {po}/{pc}")
    if "class=" in t:
        bad.append("class=")
    # ⭐ 2026-09-21 新增：正文**顶部**不得有"上一站／下一站"视觉导航。
    #   理由：粘贴到公众号后不可点击，且与公众号合集的自动导航重复，白占首屏。
    #   ⚠️ 只判"顶部导航块"，不误伤**结尾的自然预告**（如"下一站，聊最具体的一关：…"是合法承接）。
    #   顶部判定：出现在正文前 30% 且形如导航标签（"◀ 上一站：" / "下一站：" 后接标题）。
    if not LEGACY:
        top = t[: int(len(t) * 0.3)]
        nav_hits = re.findall(r"◀\s*上一站|上一站：|下一站：|▶", top)
        if len(nav_hits) >= 2:
            bad.append(f"顶部前后篇导航={len(nav_hits)}")
    p(not bad, f"{os.path.basename(d)}" + (f" ← {bad}" if bad else ""))

print("\n【7】规则化校验脚本（wx_html_fix --check）")
if TOOLS:
    sc_path = os.path.join(TOOLS, "微信HTML规范校验修复_wx_html_fix.py")
    r = subprocess.run([sys.executable, sc_path, "--check"] +
                       sorted(glob.glob(os.path.join(BASE, "发布包_*", "长图文发布包", "正文_*.html")))
                       + sorted(glob.glob(os.path.join(BASE, "发布包_*", "正文_*.html"))),
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    tail = [l for l in r.stdout.strip().splitlines() if l.strip()]
    p(bool(tail) and f"合格 {N} / {N}" in tail[-1], tail[-1] if tail else "脚本无输出")
else:
    p(False, "未找到 工具脚本/微信HTML规范校验修复_wx_html_fix.py")

print("\n【8】合并预览页")
pv = glob.glob(os.path.join(BASE, "_预览", "*全部正文预览*"))
if not pv:
    pv = glob.glob(os.path.join(BASE, "*全部正文预览*.html"))
p(bool(pv), f"预览页 {len(pv)} 个：{[os.path.basename(x) for x in pv]}")
if pv:
    # 取篇数最多的那个作为"主预览页"（历史遗留的小篇数页不计）
    # 注意：①只匹配 class="art"/'art'（正文容器，可能带 show）不匹配 arttag（导航标签）
    #       ②兼容单引号与双引号两种属性写法
    best, best_n = None, -1
    for f in pv:
        html = open(f, encoding="utf-8").read()
        n = len(re.findall(r"""class=["']art(?:\s+show)?["']""", html))
        if n > best_n:
            best, best_n = f, n
    p(best_n == N, f"主预览页含 {best_n} 篇正文（应为 {N}）｜{os.path.basename(best)}")
    if len(pv) > 1:
        print(f"  ℹ️  另有 {len(pv)-1} 个历史预览页（旧篇数的中间版本），可自行清理")
    if os.path.dirname(best) == BASE:
        print("  ℹ️  提示：预览页位于根目录。新规范建议放到独立 _预览/ 子目录，")
        print("      因为预览面板会把渲染后的 DOM 写回被打开的那个 .html（注入 data-*），")
        print("      放副本目录可让源正文物理上不被污染。旧系列可保持原状。")

print("\n【9】源正文 data-* 零残留（预览污染隔离）")
tot = sum(len(re.findall(r"\sdata-[a-zA-Z0-9_-]+=", open(f, encoding="utf-8").read()))
          for f in glob.glob(os.path.join(BASE, "发布包_*", "正文_*.html")))
p(tot == 0, f"全部源正文 data-* 计数 = {tot}")

print("\n" + "=" * 62)
print("总判定：" + ("✅ 全部通过，可交付" if ok_all else "❌ 存在未通过项，需修复后复检"))
print("=" * 62)
sys.exit(0 if ok_all else 1)
