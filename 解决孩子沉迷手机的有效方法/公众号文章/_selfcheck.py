# -*- coding: utf-8 -*-
"""发布前全套自检（第9步）：四件套完整性、标题三处一致、规范校验、篇号连续。

用法：python _selfcheck.py
"""
import re, glob, os, subprocess, sys

BASE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(os.path.dirname(os.path.dirname(BASE)), "工具脚本")
PY = sys.executable
SERIES = "解决孩子沉迷手机的有效方法"
N = 8

norm = lambda s: re.sub(r'[，,：:。、\u201c\u201d"\u300c\u300d《》\s]', '', s)
ok_all = True


def p(flag, msg):
    global ok_all
    if not flag:
        ok_all = False
    print(("  ✅ " if flag else "  ❌ ") + msg)


print("=" * 60)
print(f"《{SERIES}》发布前全套自检")
print("=" * 60)

pkgs = sorted(glob.glob(os.path.join(BASE, "发布包_*")))
print(f"\n【1】发布包数量与篇号连续：{len(pkgs)} 个")
p(len(pkgs) == N, f"共 {len(pkgs)} 篇（应为 {N} 篇）")
nums = []
for d in pkgs:
    m = re.search(r"第(\d+)篇", os.path.basename(d))
    nums.append(int(m.group(1)) if m else 0)
p(nums == list(range(1, N + 1)), f"篇号 = {nums}（应连续 1..{N}）")

print("\n【2】四件套齐全（正文html + 01字段 + 02指南）")
for d in pkgs:
    fs = os.listdir(d)
    h = [f for f in fs if f.startswith("正文_") and f.endswith(".html")]
    a = [f for f in fs if f.startswith("01_")]
    b = [f for f in fs if f.startswith("02_")]
    n = len(h) + len(a) + len(b)
    p(n == 3, f"{os.path.basename(d)}：正文{len(h)} / 01:{len(a)} / 02:{len(b)}")

print("\n【3】标题三处逐字一致（正文大标题 = 01字段表【标题】）")
for d in pkgs:
    hf = glob.glob(os.path.join(d, "正文_*.html"))[0]
    tf = glob.glob(os.path.join(d, "01_*.txt"))[0]
    head = "".join(re.findall(r'display:block;">([^<]+)</p>', open(hf, encoding="utf-8").read()))
    ti = re.search(r"【标题】[^\n]*\n([^\n]+)", open(tf, encoding="utf-8").read()).group(1).strip()
    p(norm(head) == norm(ti), f"{os.path.basename(d)}｜{ti}")

print("\n【4】来源声明在位（扶鹰教育-王金海课程口径）")
for d in pkgs:
    hf = glob.glob(os.path.join(d, "正文_*.html"))[0]
    t = open(hf, encoding="utf-8").read()
    p("扶鹰教育-王金海课程" in t and "非原文摘录" in t, os.path.basename(d))

print("\n【5】无动作指令 / 无绝对化承诺")
BAD_ACT = ["点在看", "点赞", "求关注", "转发、", "分享给", "扫码关注"]
BAD_ABS = ["一定能", "保证能", "必然", "彻底根治", "百分之百"]
for d in pkgs:
    hf = glob.glob(os.path.join(d, "正文_*.html"))[0]
    t = open(hf, encoding="utf-8").read()
    hit = [w for w in BAD_ACT + BAD_ABS if w in t]
    p(not hit, f"{os.path.basename(d)}" + (f" ← {hit}" if hit else ""))

print("\n【6】结构规范（零 table/div/img/data-*，section 配平）")
for d in pkgs:
    hf = glob.glob(os.path.join(d, "正文_*.html"))[0]
    t = open(hf, encoding="utf-8").read()
    ntab = len(re.findall(r"<table[ >]", t))
    ndiv = len(re.findall(r"<div[ >]", t))
    nimg = len(re.findall(r"<img[ >]", t))
    ndata = len(re.findall(r"\sdata-[a-zA-Z0-9_-]+=", t))
    so, sc = len(re.findall(r"<section[ >]", t)), len(re.findall(r"</section>", t))
    bad = []
    if ntab: bad.append(f"table={ntab}")
    if ndiv: bad.append(f"div={ndiv}")
    if nimg: bad.append(f"img={nimg}")
    if ndata: bad.append(f"data-*={ndata}")
    if so != sc: bad.append(f"section {so}/{sc}")
    p(not bad, f"{os.path.basename(d)}" + (f" ← {bad}" if bad else ""))

print("\n【7】规则化校验脚本（wx_html_fix --check）")
r = subprocess.run([PY, os.path.join(TOOLS, "微信HTML规范校验修复_wx_html_fix.py"), "--check"] +
                   sorted(glob.glob(os.path.join(BASE, "发布包_*", "正文_*.html"))),
                   capture_output=True, text=True, encoding="utf-8")
tail = [l for l in r.stdout.strip().splitlines() if l.strip()][-1]
p("合格 8 / 8" in tail, tail)

print("\n【8】预览合并页（_预览/ 独立目录，防写回污染）")
pv = glob.glob(os.path.join(BASE, "_预览", f"*全部正文预览*"))
p(bool(pv), f"预览页 {len(pv)} 个：{[os.path.basename(x) for x in pv]}")
if pv:
    t = open(pv[0], encoding="utf-8").read()
    arts = len(re.findall(r'class="art', t))
    p(arts == N, f"合并页含 {arts} 篇正文（应为 {N}）")

print("\n【9】源正文 data-* 零残留（预览污染隔离）")
src = sorted(glob.glob(os.path.join(BASE, "发布包_*", "正文_*.html")))
tot = sum(len(re.findall(r"\sdata-[a-zA-Z0-9_-]+=", open(f, encoding="utf-8").read())) for f in src)
p(tot == 0, f"全部源正文 data-* 计数 = {tot}")

print("\n" + "=" * 60)
print("总判定：" + ("✅ 全部通过，可交付" if ok_all else "❌ 存在未通过项，需修复后复检"))
print("（封面 .jpg 待 Gate 3 确认风格后生成，本轮未入包）")
print("=" * 60)
