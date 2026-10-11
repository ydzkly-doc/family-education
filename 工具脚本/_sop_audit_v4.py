# -*- coding: utf-8 -*-
# 按新 SOP（09-distribution）六维巡检 v4 33 条，只报告不改稿。
import os, re, glob, io

V4 = r"D:\个人资料\家庭教育\公众号\手机方案\视频号文案_v4"

def section(text, start_pat, end_pat):
    m = re.search(start_pat + r"(.*?)" + end_pat, text, re.S)
    return m.group(1) if m else ""

def main():
    files = sorted(glob.glob(os.path.join(V4, "*", "视频号文案_*.md")),
                   key=lambda p: os.path.basename(os.path.dirname(p))[:2])
    rows = []
    for p in files:
        nn = os.path.basename(os.path.dirname(p))[:2]
        t = io.open(p, encoding="utf-8").read()

        # 口播正文（一、→ 二、）
        speech = section(t, r"## 一、口播文案", r"## 二、")
        # 口播的纯句子行（非注释、非空）
        slines = [ln.strip() for ln in speech.splitlines()
                  if ln.strip() and not ln.strip().startswith(("#", "-", "*", "【", "（"))]
        opening = slines[0] if slines else ""
        opening2 = slines[1] if len(slines) > 1 else ""

        # 版本
        ver = re.search(r"\*\*版本\*\*[：:]\s*(\S+)", t)
        ver = ver.group(1) if ver else "?"

        # 封面
        cov = re.search(r"\*\*封面大字\*\*[：:]\s*(.+)", t)
        cov = cov.group(1).strip() if cov else "?"

        # 强调句（上屏方案 强调句小节）
        emph = section(t, r"### 强调句", r"### 金句大字卡")
        emph_lines = [re.sub(r"^[\d\.\-\s]+", "", x.strip())
                      for x in emph.splitlines() if x.strip().startswith(("1", "2", "3", "4", "5", "6", "-"))]

        # 结尾开放提问：口播里最后含问号的句子
        questions = [s for s in slines if s.endswith("？") or s.endswith("?")]
        last_q = questions[-1] if questions else ""

        rows.append(dict(nn=nn, ver=ver, cov=cov, opening=opening,
                         opening2=opening2, last_q=last_q))

    for r in rows:
        print("【%s】版本=%s" % (r["nn"], r["ver"]))
        print("  封面: %s" % r["cov"])
        print("  口播首句: %s" % r["opening"])
        if r["opening2"]:
            print("  口播次句: %s" % r["opening2"])
        if r["last_q"]:
            print("  末问句: %s" % r["last_q"])
        print()

main()
