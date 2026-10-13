# -*- coding: utf-8 -*-
"""歌曲 × 课标词汇 覆盖率分析（lemma 词形归并）。
做法：
  1) 歌词切词 -> 对每个 token 求 lemma（lemminflect，按 VERB/NOUN 多解 + 不规则表兜底）。
  2) 词表每个词也求其“可能出现的屈折形”集合（复数、时态、比较级等，用 lemminflect 反向生成），
     这样歌词里的 went/children/better 能命中词表的 go/child/good。
  3) 统计：每首命中哪些词表词；全库累计覆盖率；从未被任何歌覆盖的“缺口词”。
输出 JSON + Markdown 报告。
"""
import os, re, json, glob
from lemminflect import getLemma, getAllLemmas, getAllInflections

BASE = os.path.dirname(os.path.abspath(__file__))
VB = os.path.join(BASE, "词表")
LY = os.path.join(BASE, "歌词")

# lemminflect 归并不规则名词复数的盲区，手工兜底（双向）
IRREG = {
    "children": "child", "men": "man", "women": "woman", "people": "people",
    "feet": "foot", "teeth": "tooth", "mice": "mouse", "geese": "goose",
    "oxen": "ox", "lice": "louse", "dice": "die",
    "better": "good", "best": "good", "worse": "bad", "worst": "bad",
    "more": "more", "most": "most", "less": "less", "least": "little",
    "further": "far", "farther": "far", "farthest": "far", "furthest": "far",
    "i": "i", "me": "i", "my": "my", "mine": "mine",
    "am": "be", "is": "be", "are": "be", "was": "be", "were": "be",
    "been": "be", "being": "be",
    "has": "have", "had": "have", "having": "have",
    "does": "do", "did": "do", "done": "do", "doing": "do",
    "went": "go", "gone": "go",
}
# good/well 同根、bad 比较级等常见跨词性
SYN = {"well": "good", "ill": "sick"}

TOKEN = re.compile(r"[A-Za-z]+(?:'[a-z]+)?")

def lemmas_of(tok):
    """返回 token 可能归并到的原形集合（小写）。"""
    t = tok.lower()
    if t in IRREG:
        return {IRREG[t]}
    out = set()
    try:
        for upos in (None, "VERB", "NOUN", "ADJ", "ADV"):
            try:
                lem = getLemma(t, upos=upos) if upos else getLemma(t)
                for x in lem:
                    out.add(x.lower())
            except Exception:
                pass
    except Exception:
        pass
    out.add(t)
    if t in SYN:
        out.add(SYN[t])
    return out

def surface_forms(lemma_word):
    """词表词 -> 歌词中可能出现的形态集合（含自身）。用于稳健命中。"""
    forms = {lemma_word}
    try:
        infl = getAllInflections(lemma_word)
        for _upos, lst in infl.items():
            for x in lst:
                forms.add(x.lower())
    except Exception:
        pass
    # 手工不规则反向
    rev = {
        "child": ["children"], "man": ["men"], "woman": ["women"],
        "foot": ["feet"], "tooth": ["teeth"], "mouse": ["mice"], "goose": ["geese"],
        "good": ["better", "best", "well"], "bad": ["worse", "worst", "ill"],
        "far": ["further", "farther", "farthest", "furthest"],
        "little": ["less", "least"],
        "go": ["went", "gone"], "have": ["has", "had"], "do": ["does", "did", "done"],
        "be": ["am", "is", "are", "was", "were", "been", "being"],
    }
    for x in rev.get(lemma_word, []):
        forms.add(x)
    return forms

def load_vocab(path):
    return [w.strip().lower() for w in open(path, encoding="utf-8") if w.strip()]

def song_tokens(path):
    text = open(path, encoding="utf-8").read().lower()
    return TOKEN.findall(text)

def analyze_vocab(vocab_set, label):
    vocab_set = set(vocab_set)
    surf2vocab = {}
    for w in vocab_set:
        for sf in surface_forms(w):
            surf2vocab.setdefault(sf, w)
        surf2vocab[w] = w

    songs = sorted(glob.glob(os.path.join(LY, "*.txt")))
    per_song = []
    total_hits = set()
    for sp in songs:
        key = os.path.splitext(os.path.basename(sp))[0]
        toks = song_tokens(sp)
        lemma_set = set()
        for t in toks:
            lemma_set |= lemmas_of(t)
        hits = set()
        for t in set(toks):
            if t in vocab_set:
                hits.add(t)
            if t in surf2vocab:
                hits.add(surf2vocab[t])
        for lm in lemma_set:
            if lm in vocab_set:
                hits.add(lm)
            if lm in surf2vocab:
                hits.add(surf2vocab[lm])
        hits &= vocab_set
        per_song.append({"key": key, "tokens": len(toks),
                         "hits": sorted(hits), "n_hit": len(hits)})
        total_hits |= hits

    missing = sorted(vocab_set - total_hits)
    return {
        "label": label,
        "vocab_size": len(vocab_set),
        "covered": len(total_hits),
        "rate": round(len(total_hits) / len(vocab_set) * 100, 1),
        "per_song": per_song,
        "missing": missing,
        "covered_words": sorted(total_hits),
    }

def analyze(vocab_path, label):
    vocab = load_vocab(vocab_path)
    return analyze_vocab(vocab, label)

def main():
    zk = set(load_vocab(os.path.join(VB, "中考_词条.txt")))
    gk = set(load_vocab(os.path.join(VB, "高考3500_词条.txt")))
    union = zk | gk
    res = {
        "中考（初中~1600）": analyze_vocab(zk, "中考（初中~1600）"),
        "高考3500（高中增量口径）": analyze_vocab(gk, "高考3500（高中增量口径）"),
        "完整课标（中考∪高考）": analyze_vocab(union, "完整课标（中考∪高考）"),
    }
    with open(os.path.join(BASE, "覆盖分析结果.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    for lab, r in res.items():
        print(f"\n### {lab}: 词表 {r['vocab_size']}，全库覆盖 {r['covered']}，覆盖率 {r['rate']}%")
        print("命中最多的 12 首：")
        for s in sorted(r["per_song"], key=lambda x: -x["n_hit"])[:12]:
            print(f"  {s['key']:22s} 命中 {s['n_hit']:4d}（{s['tokens']} 词次）")
        print(f"缺口词 {len(r['missing'])} 个（示例 40）：", ", ".join(r["missing"][:40]))

if __name__ == "__main__":
    main()
