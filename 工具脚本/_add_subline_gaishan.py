# -*- coding: utf-8 -*-
"""给《改善你的亲子关系》12 条 md 的「### 封面」节补一行副标（新标准 md 写法）。
在大字行后插入：- 副标：**…**（幂等：已有副标行则跳过）。
"""
import io
import os

BASE = r"D:\个人资料\家庭教育\公众号\改善你的亲子关系\视频号文案"
SUBS = {
    "01": "听话，不等于关系好",
    "02": "他不是没想法，是不想说了",
    "03": "说得对，不等于听得进",
    "04": "先接消息，再处理问题",
    "05": "熟，不等于可以不尊重",
    "06": "一天的话，抽出来看看",
    "07": "对不起，别急着辩护",
    "08": "说到能放下，才算清",
    "09": "共情，不等于同意",
    "10": "能执行的规则问四件事",
    "11": "存进去的，是底气",
    "12": "安全边界，不能等",
}

for no, sub in SUBS.items():
    hit = None
    for d in os.listdir(BASE):
        if d.startswith(no + "_") and os.path.isdir(os.path.join(BASE, d)):
            hit = d
            break
    if not hit:
        print(f"[MISS dir] {no}")
        continue
    md = None
    for f in os.listdir(os.path.join(BASE, hit)):
        if f.endswith(".md") and f.startswith("视频号文案_"):
            md = os.path.join(BASE, hit, f)
            break
    if not md:
        print(f"[MISS md] {no}")
        continue
    with io.open(md, "r", encoding="utf-8") as fp:
        lines = fp.readlines()
    if any("副标：" in ln for ln in lines):
        print(f"[skip] {no} 已有副标行")
        continue
    out, done = [], False
    for ln in lines:
        out.append(ln)
        if not done and ln.strip().startswith("- 大字："):
            out.append("- 副标：**%s**\n" % sub)
            done = True
    if not done:
        print(f"[FAIL] {no} 没找到大字行")
        continue
    with io.open(md, "w", encoding="utf-8") as fp:
        fp.writelines(out)
    print(f"[ok] {no} <- 副标：{sub}")
print("done")
