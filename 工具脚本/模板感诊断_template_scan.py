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
    --json      以 JSON 输出，便于脚本消费

节流线（超线会标 ★）：
    我后来试着做的几件小事   应仅出现在方法类文章（>0 即提示）
    不是……而是……            单篇 ≤2 次
    那一刻/慢慢/一点点/我忽然  单篇合计 ≤3 次
    愿你……                   不每篇都用
    初三年级词                与"高一"人设冲突
"""
import re, glob, os, sys, argparse, json

# 节流线配置
THRESH = {
    "buer": 2,        # 不是…而是… 单篇上限
    "same_word": 3,   # 那一刻+慢慢+一点点+我忽然 合计上限
}

PAT_BUER = re.compile(r"不是.{1,30}?而是")
SAME_WORDS = ["那一刻", "慢慢", "一点点", "我忽然", "我突然"]
GRADE_WORDS = ["初三", "中考", "初二", "初升高"]
EXPECT_GRADE = ["高一", "高二"]   # 人设应为高中段


def visible_text(html: str) -> str:
    """去 script/style/标签，得到可见文字。"""
    body = re.sub(r"<(script|style)\b.*?</\1>", "", html, flags=re.S | re.I)
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
    ap.add_argument("--json", action="store_true", help="JSON 输出")
    ap.add_argument("--count", action="store_true",
                    help="只报可见字符数 + 区间判定（普通稿 1600-2400 / 速览 900-1400）")
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
        hfs = glob.glob(os.path.join(d, "正文_*.html"))
        if not hfs:
            continue
        html = open(hfs[0], encoding="utf-8").read()
        vis = visible_text(html)
        n = re.search(r"第(\d+)篇", os.path.basename(d))
        same = sum(vis.count(w) for w in SAME_WORDS)
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
        )
        warns = []
        if row["small"]:
            warns.append("含'小事情'模块")
        if row["buer"] > THRESH["buer"]:
            warns.append(f"不是而>2({row['buer']})")
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

    # ---- --count 模式：可见字符数 + 区间判定（普通稿 1600–2400 / 速览 900–1400）----
    if args.count:
        print(f"=== 篇幅诊断：{os.path.basename(base)}（{len(rows)} 篇）===")
        print(f"参考区间：普通完整稿 1600–2400（轻稿 1600–1900 / 深度稿 1900–2400）；速览短答 900–1400")
        print(f"{'篇':>3} {'字数':>6} {'区间判定':<28}  标题")
        print("-" * 96)
        short = long_ = okn = 0
        baseline = None
        if args.baseline:
            baseline = os.path.abspath(args.baseline)
        for r in rows:
            c = r["chars"]
            if c < 900:
                verdict, mark = "严重偏薄（<900）", "❌"
                short += 1
            elif c < 1400:
                verdict, mark = "偏薄（900–1400，仅限速览/短答）", "⚠️"
                short += 1
            elif c < 1600:
                # 1400–1600：既不达普通稿下限，也不是"速览短答"体量——典型的"差一点没写足"
                verdict, mark = "偏薄（1400–1600，未达普通稿下限）", "⚠️"
                short += 1
            elif c <= 2400:
                verdict, mark = "正常区间", "✅"
                okn += 1
            else:
                verdict, mark = "偏长（>2400）", "⚠️"
                long_ += 1
            extra = ""
            if baseline:
                # 尝试按篇号匹配基线正文，做 30% 降幅复核
                cands = glob.glob(os.path.join(baseline, "正文_*.html"))
                hit = [f for f in cands if re.search(r"第0*%d篇" % r["n"], os.path.basename(f))]
                if hit:
                    old = len(re.sub(r"\s", "", visible_text(open(hit[0], encoding="utf-8").read())))
                    if old:
                        drop = (old - c) / old * 100
                        extra = f"  原 {old} → 降幅 {drop:.0f}%" + ("  ★≥30% 须复核四要点" if drop >= 30 else "")
            print(f"{r['n']:>3} {c:>6} {mark} {verdict:<26}  {r['title'][:30]}{extra}")
        print("-" * 96)
        print(f"正常 {okn} ／ 偏薄 {short} ／ 偏长 {long_}")
        print("提示：区间是报警器不是配额；偏长不等于要删——先确认五层完整性是否真的冗余。")
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
