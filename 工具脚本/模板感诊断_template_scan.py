# -*- coding: utf-8 -*-
"""
模板感 / 表达节流 诊断（通用版）

对应专家 wechat-article-studio SOP 第 2 步「打破模板感」的句式节流指标，
以及第 9 步自检中的人物时间线一致性检查。

用法：
    python 模板感诊断_template_scan.py --dir "某系列/公众号文章"
    python 模板感诊断_template_scan.py --dir "某系列/公众号文章" --diag-structure

参数：
    --dir       成果根目录（默认当前目录）
    --diag-structure  额外输出每篇的结构特征（竖条小标题、卡片、疑似模块），
                      用于判断"6 种文章结构是否被轮换使用"
    --diag-openers    跨篇开篇去同质化诊断：报出同系列内「同时段＋同空间」的重复开篇
    --count     篇幅诊断：可见字符数 + 体裁分档判定（叙事型 2000–2800 / 方法型 1200–1800）
    --baseline  <目录>  与改动前备份对比，做 30% 降幅复核
    --json      以 JSON 输出，便于脚本消费

节流线（超线会标 ★）：
    我后来试着做的几件小事   应仅出现在方法类文章（>0 即提示）
    不是……而是……            目标 ≤1 次；硬上限 2（提示级）；≥3 次进 ★ 强制复核
    那一刻/慢慢/一点点/我忽然  单篇合计 ≤3 次
    愿你……                   不每篇都用
    初三年级词                与"高一"人设冲突
"""
import re, glob, os, sys, argparse, json

# 节流线配置（2026-09-28 收紧：「不是…而是…」改为「目标≤1 / 硬上限2 / ≥3复核」）
THRESH = {
    "buer": 1,         # 不是…而是… 目标上限（写作时应压到 1 次以内）
    "buer_hard": 2,    # 硬上限；≥3 次进 ★ 警告，须逐句复核并写明保留理由
    "same_word": 3,    # 那一刻+慢慢+一点点+我忽然 合计上限
}

# 开篇取样长度与「三要素」词表（跨篇开篇去同质化，见 SOP 02-writing.md）
OPENER_HEAD = 600
OPEN_WORDS = {
    "时段": ["清晨", "早上", "早晨", "上午", "中午", "下午", "傍晚", "晚上",
             "夜里", "深夜", "半夜", "凌晨", "晚饭", "饭桌", "放学", "周末"],
    "空间": ["玄关", "门口", "门外", "房门", "卧室", "客厅", "厨房", "车里",
             "车上", "校门", "学校", "饭桌", "餐桌", "卫生间", "阳台", "沙发", "走廊"],
    "触发": ["摔门", "反锁", "砰", "夺过", "抢过", "路由器", "放下书包", "放下碗",
             "没说话", "沉默", "来电", "电话", "消息", "卷子", "成绩"],
}


def opener_tags(vis: str) -> dict:
    """取开篇「时段/空间/触发」三要素（每维取正文中**最靠前**命中的那个词）

    取「最靠前」而非词表顺序，是为了跳过正文开头的改编声明/引荐块——
    那些段落不含场景词，第一次命中的位置自然落在正文开篇句上。
    """
    head = re.sub(r"\s", "", vis)[:OPENER_HEAD]
    out = {}
    for dim, words in OPEN_WORDS.items():
        best, pos = "", len(head) + 1
        for w in words:
            i = head.find(w)
            if 0 <= i < pos:
                best, pos = w, i
        out[dim] = best
    return out


# 段落节奏：单个「叙述段」的字数参考线（2026-09-28 立，**实测校准**）
#   实测 5 个系列：>90 字是**常态**（几乎每篇都有），毫无区分度；
#   最长段实测最大值 99／122／178／187／236 → 取 **180 字（约 8–9 行）** 作参考线。
#   ⚠️ 超线只提示"看一眼要不要拆"，**不是不合格**；**不得为拆段牺牲连贯**（见 SOP「连贯优先」）。
#   ⚠️ 只统计**叙述段**（不含 <br> 的 <p>）——含 <br> 的是结构化卡／清单，不适用本判据。
PARA_MAX = 180


def para_lengths(html: str):
    """各「叙述段」的可见字数（排除含 <br> 的结构化卡）。"""
    out = []
    for m in re.finditer(r"<p\b[^>]*>(.*?)</p>", html, re.S):
        inner = m.group(1)
        if "<br" in inner:
            continue
        t = re.sub(r"<[^>]+>", "", inner)
        t = re.sub(r"\s", "", t).replace("&nbsp;", "")
        if t:
            out.append(len(t))
    return out


# 体裁辅助判据：正文叙述占比（2026-09-28 立）
#   SOP 篇幅已按体裁分档（叙事型 2000–2800 / 方法型 1200–1800），
#   "这篇是叙事还是方法"不能靠感觉——用**正文叙述段字数占全文的比例**提示。
#   正文叙述段 = 非居中 且 font-size ≥15.5px 的 <p>（改前只按"有无 <br>"分，
#   结果把 14px 的卡片说明也当成正文 → 全库恒为 90%+，毫无区分度，已修正）。
NARR_HI, NARR_LO = 0.60, 0.40


def narr_stats(html: str):
    """→ (正文叙述段字数, 卡片/说明段字数)。"""
    body = other = 0
    for m in re.finditer(r"<p\b([^>]*)>(.*?)</p>", html, re.S):
        style, inner = m.group(1), m.group(2)
        t = re.sub(r"<[^>]+>", "", inner)
        t = re.sub(r"\s", "", t).replace("&nbsp;", "")
        if not t:
            continue
        s = style.replace(" ", "")
        m2 = re.search(r"font-size:([\d.]+)px", s)
        fs = float(m2.group(1)) if m2 else 16.0
        if fs >= 15.5 and "text-align:center" not in s:
            body += len(t)
        else:
            other += len(t)
    return body, other

PAT_BUER = re.compile(r"不是.{1,30}?而是")
SAME_WORDS = ["那一刻", "慢慢", "一点点", "我忽然", "我突然"]
GRADE_WORDS = ["初三", "中考", "初二", "初升高"]
EXPECT_GRADE = ["高一", "高二"]   # 人设应为高中段


def visible_text(html: str) -> str:
    """去 head/script/style/标签，得到可见文字。

    ⚠️ 必须去掉 <head>：否则 <title> 里的句式（例如标题本身写成"不是…而是…"）
    会被计入**正文**配额——标题句式归第 1 步「标题三类轮换」管，不是正文指纹。
    （2026-09-28 修：第 14 篇曾因此被误报 3 次，实际正文只有 1 次。）
    """
    body = re.sub(r"<head\b.*?</head>", "", html, flags=re.S | re.I)
    body = re.sub(r"<(script|style)\b.*?</\1>", "", body, flags=re.S | re.I)
    return re.sub(r"<[^>]+>", "", body)


def head_title(html: str) -> str:
    """抽顶部白字大标题（兼容两种历史写法）。"""
    cands = []
    for m in re.finditer(r'<p[^>]*>([^<]+)</p>', html):
        tag, x = m.group(0), m.group(1).strip()
        if "#ffffff" in tag.lower() and "font-weight:bold" in tag.replace(" ", ""):
            cands.append(x)
        if len(cands) >= 2:
            break
    return "".join(cands)


def structure_profile(html: str) -> dict:
    """结构特征：竖条小标题、卡片数、疑似固定模块。"""
    return dict(
        subs=re.findall(r'border-left:5px solid[^>]*>(?:<span[^>]*>)?([^<]+)', html),
        cards=len(re.findall(r'border-radius:\s*(?:8|10)px', html)),
        quote_blocks=html.count("text-align:center"),
        has_small_module="我后来试着做的几件小事" in html,
        has_faq=bool(re.search(r"问题[一二三四五]：", html)),
        has_letter=bool(re.search(r"第[一二三]封信|一封信", html)),
        has_dialogue=bool(re.search(r"拆第[一二三]句", html)),
        has_replay=bool(re.search(r"复盘[一二三四]", html)),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=".", help="成果根目录")
    ap.add_argument("--diag-structure", action="store_true", help="额外输出结构特征")
    ap.add_argument("--diag-openers", action="store_true",
                    help="跨篇开篇去同质化：报出同系列内「同时段＋同空间」的重复开篇")
    ap.add_argument("--json", action="store_true", help="JSON 输出")
    ap.add_argument("--count", action="store_true",
                    help="只报可见字符数 + 体裁分档判定（叙事型 2000-2800 / 方法型 1200-1800；1800-2000 过渡带）")
    ap.add_argument("--baseline", default=None,
                    help="对比基线目录（如改动前的备份目录）：用于 30%% 降幅复核线")
    args = ap.parse_args()

    base = os.path.abspath(args.dir)
    pkgs = sorted(
        [d for d in glob.glob(os.path.join(base, "发布包_*")) if os.path.isdir(d)],
        key=lambda p: int(re.search(r"第(\d+)篇", os.path.basename(p)).group(1))
        if re.search(r"第(\d+)篇", os.path.basename(p)) else 999,
    )
    if not pkgs:
        print(f"未找到发布包：{base}")
        return 1

    rows = []
    for d in pkgs:
        _cdir = os.path.join(d, "长图文发布包")
        if not os.path.isdir(_cdir):
            _cdir = d
        hfs = glob.glob(os.path.join(_cdir, "正文_*.html"))
        if not hfs:
            continue
        html = open(hfs[0], encoding="utf-8").read()
        vis = visible_text(html)
        n = re.search(r"第(\d+)篇", os.path.basename(d))
        same = sum(vis.count(w) for w in SAME_WORDS)
        _pl = para_lengths(html)
        _narr, _card = narr_stats(html)
        row = dict(
            n=int(n.group(1)) if n else 0,
            name=os.path.basename(d),
            title=head_title(html),
            chars=len(re.sub(r"\s", "", vis)),
            small=vis.count("我后来试着做的几件小事"),
            moment=vis.count("那一刻"),
            manman=vis.count("慢慢"),
            yidiandian=vis.count("一点点"),
            huran=vis.count("我忽然") + vis.count("我突然"),
            same_total=same,
            buer=len(PAT_BUER.findall(vis)),
            yuan=vis.count("愿你"),
            grades={g: vis.count(g) for g in GRADE_WORDS if vis.count(g)},
            otags=opener_tags(vis),
            max_para=max(_pl) if _pl else 0,                  # 最长"叙述段"字数
            over_para=sum(1 for x in _pl if x > PARA_MAX),    # 超长叙述段条数
            narr_ratio=(_narr / (_narr + _card)) if (_narr + _card) else 0.0,  # 叙述段占比（判体裁用）
        )
        warns = []
        if row["small"]:
            warns.append("含'小事情'模块")
        if row["buer"] > THRESH["buer_hard"]:
            warns.append(f"不是而{row['buer']}次·须逐句复核")
        elif row["buer"] > THRESH["buer"]:
            warns.append("不是而2次·建议压到1")
        if same > THRESH["same_word"]:
            warns.append(f"同类词>3({same})")
        if row["yuan"]:
            warns.append("愿你")
        if row["grades"]:
            warns.append("年级冲突" + str(row["grades"]))
        row["warns"] = warns
        if args.diag_structure:
            row["struct"] = structure_profile(html)
        rows.append(row)

    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0

    # ---- --count 模式：可见字符数 + 体裁分档判定（2026-09-28 起按体裁分档）----
    if args.count:
        print(f"=== 篇幅诊断：{os.path.basename(base)}（{len(rows)} 篇）===")
        print("参考档位（按体裁）：叙事型 2000–2800 ／ 方法型 1200–1800"
              "（1800–2000 为两档过渡带）／ 速览短答 900–1400")
        print(f"{'篇':>3} {'字数':>6} {'正文%':>6} {'叙事档':<6} {'方法档':<6}  标题")
        print("-" * 96)
        n_ok = m_ok = both_bad = 0
        n_hi = n_lo = 0
        baseline = None
        if args.baseline:
            baseline = os.path.abspath(args.baseline)

        def _verdict(c, lo, hi, soft_lo=None, soft_hi=None):
            if c < lo:
                return "过渡" if (soft_lo and c >= soft_lo) else "偏薄"
            if c <= hi:
                return "✅"
            if soft_hi and c <= soft_hi:
                return "过渡"
            return "偏长"

        for r in rows:
            c = r["chars"]
            vn = _verdict(c, 2000, 2800, soft_lo=1800)
            vm = _verdict(c, 1200, 1800, soft_hi=2000)
            if vn == "✅":
                n_ok += 1
            if vm == "✅":
                m_ok += 1
            if vn != "✅" and vm != "✅":
                both_bad += 1
            nr = r.get("narr_ratio", 0.0)
            if nr >= NARR_HI:
                n_hi += 1
            elif nr <= NARR_LO:
                n_lo += 1
            extra = ""
            if baseline:
                # 尝试按篇号匹配基线正文，做 30% 降幅复核
                _bdir = os.path.join(baseline, "长图文发布包")
                if not os.path.isdir(_bdir):
                    _bdir = baseline
                cands = glob.glob(os.path.join(_bdir, "正文_*.html"))
                hit = [f for f in cands if re.search(r"第0*%d篇" % r["n"], os.path.basename(f))]
                if hit:
                    old = len(re.sub(r"\s", "", visible_text(open(hit[0], encoding="utf-8").read())))
                    if old:
                        drop = (old - c) / old * 100
                        extra = f"  原 {old} → 降幅 {drop:.0f}%" + ("  ★≥30% 须复核四要点" if drop >= 30 else "")
            _pq = f"  ★超长段×{r['over_para']}" if r.get("over_para") else ""
            print(f"{r['n']:>3} {c:>6} {nr * 100:>5.0f}% {vn:<6} {vm:<6}  "
                  f"{r['title'][:30]}{_pq}{extra}")
        print("-" * 96)
        print(f"叙事档合格 {n_ok} ／ 方法档合格 {m_ok} ／ 两档皆不合格 {both_bad}")
        print(f"体裁提示（按正文叙述占比）：偏叙事型(≥60%) {n_hi} ／ 偏方法型(≤40%) {n_lo} ／ "
              f"混合 {len(rows) - n_hi - n_lo}　← 仅辅助，实际档位以规划表「篇职能」为准")
        _po = sum(1 for r in rows if r.get("over_para"))
        print(f"段落节奏：{_po} 篇含超长叙述段（单段 >{PARA_MAX} 字，约 8–9 行）"
              + ("（全部达标）" if not _po else ""))
        print("提示：区间是报警器不是配额；偏长不等于要删——先确认五层完整性是否真的冗余。")
        print("      ⚠️ 收官篇的「工具合集／总导航」卡片区属附录，**单独计**，不并入正文档（见 SOP 篇幅条）。")
        return 0

    print(f"=== 模板感 / 表达节流诊断：{os.path.basename(base)}（{len(rows)} 篇）===")
    print(f"{'篇':>3} {'标题':<30} {'字数':>5} {'小事':>4} {'不是而':>5} "
          f"{'同类词':>5} {'愿你':>4}")
    print("-" * 84)
    hit = 0
    for r in rows:
        print(f"{r['n']:>3} {r['title'][:28]:<30} {r['chars']:>5} {r['small']:>4} "
              f"{r['buer']:>5} {r['same_total']:>5} {r['yuan']:>4}"
              + (f"   ★ {'、'.join(r['warns'])}" if r["warns"] else ""))
        if r["warns"]:
            hit += 1
    print("-" * 84)
    print(f"命中节流线：{hit}/{len(rows)} 篇"
          + ("（全部达标）" if hit == 0 else ""))

    if args.diag_structure:
        print("\n=== 结构轮换诊断（判断是否 6 种结构轮换使用）===")
        print(f"{'篇':>3} {'竖条小标题':<6} {'卡片':>4} {'金句块':>5}  结构标记")
        for r in rows:
            s = r["struct"]
            flags = []
            if s["has_dialogue"]:
                flags.append("对话拆解")
            if s["has_replay"]:
                flags.append("问题复盘")
            if s["has_letter"]:
                flags.append("书信")
            if s["has_faq"]:
                flags.append("自问自答")
            if s["has_small_module"]:
                flags.append("小事情模块")
            print(f"{r['n']:>3} {len(s['subs']):<6} {s['cards']:>4} "
                  f"{s['quote_blocks']:>5}  {'、'.join(flags) if flags else '（现场故事/概念解释/清单工具）'}")
            for sub in s["subs"][:5]:
                print(f"        · {sub[:44]}")

    if args.diag_openers:
        from collections import Counter
        print("\n=== 跨篇开篇去同质化诊断（核心判据：同系列内「时段」过度集中）===")
        print(f"{'篇':>3} {'时段':<8} {'空间':<7} {'触发':<10}  判定")
        print("-" * 88)
        seen_combo = {}
        for r in rows:
            t = r["otags"]
            note = ""
            if t["时段"] and t["空间"]:
                key = (t["时段"], t["空间"])
                if key in seen_combo:
                    note = f"  ★★ 与第 {seen_combo[key]} 篇 同期段＋同空间"
                else:
                    seen_combo[key] = r["n"]
            elif not any(t.values()):
                note = "  ⚠ 开篇无场景锚点（缺时段/空间/触发）"
            print(f"{r['n']:>3} {t['时段'] or '—':<8} {t['空间'] or '—':<7} "
                  f"{t['触发'] or '—':<10} {note}")
        print("-" * 88)

        tc = Counter(r["otags"]["时段"] for r in rows if r["otags"]["时段"])
        strong = sum(1 for _, v in Counter(
            (r["otags"]["时段"], r["otags"]["空间"]) for r in rows
            if r["otags"]["时段"] and r["otags"]["空间"]).items() if v > 1)
        print("时段分布：" + ("／".join(f"{k} {v} 篇" for k, v in tc.most_common())
                          if tc else "（均未识别）"))
        over = [(k, v) for k, v in tc.most_common() if v >= 3]
        if over:
            print("★ 时段过度集中：" + "；".join(f"「{k}」{v} 篇" for k, v in over)
                  + "   ← 须换掉大部分；只改时间点是「假换」（见 SOP 02-writing.md）")
        if strong:
            print(f"★ 同期段＋同空间 重复 {strong} 组，须改其中一篇的开篇设定")
        if not over and not strong:
            print("✓ 开篇时段分散，未见同质化")
    return 0


if __name__ == "__main__":
    sys.exit(main())
