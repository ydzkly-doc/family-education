# -*- coding: utf-8 -*-
"""把覆盖分析结果整理成可读 Markdown，并导出缺口词清单。"""
import os, json, csv

BASE = os.path.dirname(os.path.abspath(__file__))
res = json.load(open(os.path.join(BASE, "覆盖分析结果.json"), encoding="utf-8"))

def songs_of(r, prefix=None):
    rows = r["per_song"]
    if prefix:
        rows = [s for s in rows if s["key"].startswith(prefix)]
    return rows

def union_hits(r, prefix):
    h=set()
    for s in r["per_song"]:
        if s["key"].startswith(prefix):
            h |= set(s["hits"])
    return h

union = res["完整课标（中考∪高考）"]
gk = res["高考3500（高中增量口径）"]
zk = res["中考（初中~1600）"]

def rate_block(r):
    return (f"- 词表规模：**{r['vocab_size']} 词**\n"
            f"- 35 首歌累计覆盖：**{r['covered']} 词（{r['rate']}%）**\n")

# Hamilton 单独（A 开头 7 首）对完整课标
ham = union_hits(union, "A")
# 圈层统计
def layer(prefix):
    return union_hits(union, prefix)
L = {p: union_hits(union, p) for p in ["A","B","C","D","E"]}

lines = []
A = lines.append
A("# 歌曲 × 课标词汇 · 真实覆盖率报告（人教版口径）\n")
A("> 数据由脚本对 **真实歌词（lrclib）× 真实课标词表（中考1873 + 高考3579，并集3759）** 逐词匹配得出，")
A("> 已做词形归并（went→go、children→child、better→good），非估算。共 35 首歌。\n")
A("---\n")
A("## 一、一句话结论\n")
A(f"**这 35 首歌能在歌词中真实呈现完整课标（3759 词）里的 {union['covered']} 个，约 {union['rate']}%。**")
A("听歌能高复现地拿下的是**最高频的核心词**；剩下约七成是**歌词天然不爱用的词**（学科词、抽象书面词如 "
  "*abandon/ability/abstract/academic*），**这些必须靠课本＋在校听写解决，歌替代不了。**\n")
A("这组数字的意义不是“覆盖率高/低”，而是：**歌负责让最常用、最该形成直觉的那批词在喜欢的旋律里反复撞见；课本负责兜底全覆盖。**\n")

A("---\n")
A("## 二、三种口径的覆盖率\n")
A("| 词表口径 | 规模 | 35首累计覆盖 | 覆盖率 | 说明 |")
A("|---|---:|---:|---:|---|")
A(f"| 中考（初中~1600，含 be/go/good 等基础词） | {zk['vocab_size']} | {zk['covered']} | **{zk['rate']}%** | 基础高频词，歌最能帮上忙 |")
A(f"| 高考3500（高中增量口径） | {gk['vocab_size']} | {gk['covered']} | **{gk['rate']}%** | 该表默认不再列小学初中已会的基础词 |")
A(f"| 完整课标（两表并集，推荐看这个） | {union['vocab_size']} | {union['covered']} | **{union['rate']}%** | 最接近初高中全部该会的词 |")
A("")

A("---\n")
A("## 三、Hamilton 单独的贡献（孩子的兴趣核心）\n")
A(f"仅 Hamilton 7 首（圈层 A）就在完整课标里命中 **{len(ham)} 个词**，")
A(f"占 35 首总覆盖（{union['covered']}）的 **{round(len(ham)/union['covered']*100)}%**——")
A("七首歌贡献了全库近半的有效词汇，且是孩子最愿意反复听的，**单位兴趣的词汇效率最高**。\n")
A("各圈层对完整课标的累计命中：\n")
A("| 圈层 | 内容 | 命中课标词数 |")
A("|---|---|---:|")
names={"A":"Hamilton 7首","B":"音乐剧 7首","C":"迪士尼 6首","D":"叙事流行 4首","E":"入门流行 11首"}
for p in ["A","B","C","D","E"]:
    A(f"| {p} | {names[p]} | {len(L[p])} |")
A("")

A("---\n")
A("## 四、单曲命中榜（完整课标口径，Top 20）\n")
A("词次=歌词总词数；命中=该歌出现的课标不同单词数。**叙事越密、重复钩子越多，越值得精挖。**\n")
A("| 排名 | 歌曲 | 歌词词次 | 命中课标词 |")
A("|---:|---|---:|---:|")
for i,s in enumerate(sorted(union["per_song"],key=lambda x:-x["n_hit"])[:20],1):
    A(f"| {i} | {s['key']} | {s['tokens']} | {s['n_hit']} |")
A("")

A("---\n")
A("## 五、怎么用这份数据（落地建议）\n")
A("1. **主攻圈层 A（Hamilton）**：慢歌 *Wait for It / Helpless* 精挖四会词，快歌 *My Shot / Non-Stop* 练耳抓高频词——")
A("这 7 首兴趣最浓、命中最高，是发动机。")
A("2. **每周 1 首精挖**仍按 12 周模板走；一首歌真正吃透的课标词通常 40–80 个（非只 5 个——5 个是“要求四会默写”的核心，")
A("其余作为“认读/耳熟”沉淀）。")
A("3. **缺口词交给学校**：随报告导出的 `缺口词_完整课标.txt` 是这 35 首歌都没唱到的课标词，")
A("**这些正是早读＋老师听写要解决的**，家长不用硬塞进歌里。可定期把“课本新学的词”与歌单对账，画 ⭐。")
A("4. 想提升覆盖率，正确方向不是“听更多口水歌”，而是**继续加 Hamilton 全剧＋同类叙事音乐剧**（用词面宽、复现高）。")
A("   后续可把整剧 46 首、或更多音乐剧纳入，再跑一次本脚本，覆盖率会明显上升（脚本可复用）。\n")

A("---\n")
A("## 六、数据来源与可复现\n")
A("- 词表：中考《中考英语词汇表》、高考《高考英语词汇3500》（公开词表，按字母序，含音标释义）；并集去重 3759。")
A("- 歌词：lrclib.net 公开 API 抓取的纯文本歌词，35 首全部成功，人工抽查真实（见 `歌词/` 目录）。")
A("- 归并：lemminflect 词形还原 + 不规则变形表（名词复数/动词时态/比较级）。")
A("- 脚本：`parse_vocab.py`（解词表）、`fetch_lyrics.py`（抓歌词）、`analyze_coverage.py`（算覆盖）、`build_report.py`（本报告）。")
A("- 口径提醒：这是“**歌词中出现过**”的覆盖，不等于“孩子已掌握”；出现→认识→会用仍需精挖与复现。\n")

out=os.path.join(BASE,"歌曲词汇覆盖率报告.md")
open(out,"w",encoding="utf-8").write("\n".join(lines))

# 导出缺口词清单（完整课标 & 高考口径）
for r,fn in [(union,"缺口词_完整课标.txt"),(gk,"缺口词_高考3500.txt"),(zk,"缺口词_中考.txt")]:
    with open(os.path.join(BASE,fn),"w",encoding="utf-8") as f:
        f.write("\n".join(r["missing"]))
# 导出每首命中明细 CSV（完整课标）
with open(os.path.join(BASE,"单曲命中明细_完整课标.csv"),"w",encoding="utf-8-sig",newline="") as f:
    w=csv.writer(f); w.writerow(["歌曲key","歌词词次","命中课标词数","命中单词(空格分隔)"])
    for s in sorted(union["per_song"],key=lambda x:-x["n_hit"]):
        w.writerow([s["key"],s["tokens"],s["n_hit"]," ".join(s["hits"])])

print("报告已生成:",out)
print("缺口/明细文件已导出。")
