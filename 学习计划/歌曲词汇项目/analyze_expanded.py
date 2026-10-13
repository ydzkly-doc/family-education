# -*- coding: utf-8 -*-
"""扩充歌库后的覆盖率 + 贪心最小歌单选择。
- 复用 analyze_coverage 的归并/匹配函数（读 歌词/ 目录全部 .txt）。
- 对“完整课标（中考∪高考）”计算新覆盖率、各圈层贡献、边际收益曲线。
- 贪心集合覆盖：每次选“新增课标词最多”的下一首歌，输出累计曲线和前 N 首推荐歌单。
"""
import os, sys, json, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_coverage import lemmas_of, surface_forms, song_tokens, load_vocab, VB, LY

BASE = os.path.dirname(os.path.abspath(__file__))

def song_hit_set(path, surf2vocab, vocab_set):
    toks = song_tokens(path)
    lemma_set=set()
    for t in toks: lemma_set |= lemmas_of(t)
    hits=set()
    for t in set(toks):
        if t in vocab_set: hits.add(t)
        if t in surf2vocab: hits.add(surf2vocab[t])
    for lm in lemma_set:
        if lm in vocab_set: hits.add(lm)
        if lm in surf2vocab: hits.add(surf2vocab[lm])
    return hits & vocab_set

def main():
    zk=set(load_vocab(os.path.join(VB,"中考_词条.txt")))
    gk=set(load_vocab(os.path.join(VB,"高考3500_词条.txt")))
    union=zk|gk
    surf={}
    for w in union:
        surf[w]=w
        for sf in surface_forms(w): surf.setdefault(sf,w)

    files=sorted(glob.glob(os.path.join(LY,"*.txt")))
    hits={}
    tokcount={}
    for p in files:
        k=os.path.splitext(os.path.basename(p))[0]
        hs=song_hit_set(p,surf,union)
        hits[k]=hs; tokcount[k]=song_tokens(p).__len__()
    total=set().union(*hits.values()) if hits else set()
    print(f"歌曲总数 {len(files)}；完整课标 {len(union)}；覆盖 {len(total)}；覆盖率 {round(len(total)/len(union)*100,1)}%")

    # 分前缀统计
    def layer_cov(prefix):
        s=set()
        for k,h in hits.items():
            if k.startswith(prefix): s|=h
        return s
    for pre,name in [("H","Hamilton全剧"),("M","音乐剧扩充"),("P","流行扩充"),
                     ("A","Hamilton(旧7)"),("B","音乐剧(旧)"),("C","迪士尼"),
                     ("D","叙事流行(旧)"),("E","入门流行")]:
        s=layer_cov(pre)
        print(f"  前缀 {pre} {name}: 累计命中 {len(s)}")

    # 贪心集合覆盖
    remaining=set(union)
    chosen=[]
    avail=dict(hits)
    covered=set()
    while avail:
        # 选新增最多；并列时歌词更短优先（更好学）
        best=max(avail, key=lambda k:(len(avail[k]-covered), -tokcount[k]))
        gain=len(avail[best]-covered)
        if gain==0:
            break
        covered|=avail[best]
        chosen.append((best, gain, len(covered)))
        del avail[best]

    # 输出贪心曲线关键节点
    rows=[]
    cum=0
    for i,(k,g,c) in enumerate(chosen,1):
        rows.append({"rank":i,"song":k,"gain":g,"cum":c,
                     "rate":round(c/len(union)*100,1),"tokens":tokcount[k]})
    marks=[10,20,30,40,50,60,80,100,120,len(rows)]
    print("\n贪心最小歌单累计覆盖（关键节点）：")
    for m in marks:
        if 1<=m<=len(rows):
            r=rows[m-1]
            print(f"  前 {m:3d} 首：累计 {r['cum']:4d} 词, {r['rate']}%  (第{m}首 +{r['gain']}, {r['song']})")

    out={"songs_total":len(files),"vocab_size":len(union),"covered":len(total),
         "rate":round(len(total)/len(union)*100,1),
         "greedy_order":rows}
    json.dump(out, open(os.path.join(BASE,"扩充覆盖结果.json"),"w",encoding="utf-8"),
              ensure_ascii=False,indent=2)
    print("\n已写 扩充覆盖结果.json")

if __name__=="__main__":
    main()
