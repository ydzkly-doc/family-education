#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
从文案 MD 的「二、口播文案」自动生成「三、提词器文案」。

为什么要用它（2026-09-25 立）：
    提词器文案是口播的**派生物**——手写/手改必然与口播不同步
    （实战中一次比对就报出 6 处差异：改了口播、忘了改提词器）。
    所以：**口播改完，跑一次这个脚本即可**。

用法：
    PY="C:/Users/ZhuanZ/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
    "$PY" 工具脚本/gen_prompter.py "文案.md" \
        --cuts "第1段最后一句。||第2段最后一句。||第3段最后一句。" \
        --titles "第 1 段拍（说明）||第 2 段拍（说明）||第 3 段拍（说明）||第 4 段拍（说明）"

    # 只看差异、不写入
    "$PY" 工具脚本/gen_prompter.py "文案.md" --cuts ... --titles ... --check

规则：
    · 抽取：读口播段 → 丢掉所有【方括号】提示行 → 按 。？！断句（跨行的短句会合并成一句）
    · ⚠️ **只排除【方括号】行**：口播区里 `>` 开头的 markdown 引用行会被**当成台词、原样带进提词器**
      → **口播区不要写 `>` 说明行**，要写就写到「## 二、口播文案」区块之外（2026-09-27 实测踩过：
      写在口播区的一行说明，整行出现在提词器第 1 段里，用户复制进 App 会连说明一起念）
    · 分段：`--cuts` 给「每段的最后一句」（用 || 分隔），段数 = cuts 数 + 1
    · 标题：`--titles` 给每段的说明，脚本自动补成 `——第 N 段拍（说明）——`
    · ⚠️ 生成后 `---` 前会留一个空行（否则 Markdown 会把它解析成二级标题）
"""
import argparse
import io
import re
import sys


def extract_spoken(body: str):
    """口播段 → 逐句列表（剥掉方括号提示行、去掉粗体记号）

    ⚠️ 断句要认「标点 + 右引号」的结尾——否则 '你现在卡在哪一步？"' 这种句子
       会跨到下一句去（实战踩过：01/02 的提词器都把两句粘成了一句）。
    """
    spoken = [l.strip() for l in body.split('\n') if l.strip() and not l.strip().startswith('【')]
    out, buf = [], ''
    for l in spoken:
        buf += l
        if buf and re.search(r'[。？！][\u201d"]?$', buf):
            out.append(re.sub(r'\*+', '', buf))
            buf = ''
    if buf:
        out.append(re.sub(r'\*+', '', buf))
    return out


def build_prompter(sentences, cuts, titles):
    idx = []
    for c in cuts:
        c = c.strip()
        if c not in sentences:
            raise SystemExit(f'❌ 分段锚点找不到：{c!r}\n   （它必须与口播里某一整句完全一致）')
        idx.append(sentences.index(c))
    if len(titles) != len(idx) + 1:
        raise SystemExit(f'❌ 段标题数({len(titles)})应比锚点数({len(idx)})多 1')

    seg, start = [], 0
    for e in idx:
        seg.append(sentences[start:e + 1])
        start = e + 1
    seg.append(sentences[start:])

    out = []
    for i, (t, s) in enumerate(zip(titles, seg), 1):
        out.append(f'——第 {i} 段拍（{t}）——')
        out.extend(s)
        out.append('')
    return '\n'.join(out).rstrip() + '\n\n'   # ⚠️ 末尾留空行，保住后面的 ---


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('md', help='文案 MD 路径')
    ap.add_argument('--cuts', required=True, help='每段最后一句，用 || 分隔')
    ap.add_argument('--titles', required=True, help='每段说明（不含"第 N 段拍"），用 || 分隔')
    ap.add_argument('--check', action='store_true', help='只比对，不写入')
    a = ap.parse_args()

    t = io.open(a.md, encoding='utf-8').read()

    m = re.search(r'## 二、口播文案\n(.*?)\n---\n', t, re.S)
    if not m:
        raise SystemExit('❌ 找不到「## 二、口播文案」区块（或它后面没有 --- 分隔）')
    sentences = extract_spoken(m.group(1))

    cuts = [c for c in a.cuts.split('||') if c.strip()]
    titles = [x.strip() for x in a.titles.split('||') if x.strip()]
    prompter = build_prompter(sentences, cuts, titles)

    # 定位「三、提词器文案」区块（到下一个 --- 为止）
    i = t.index('## 三、提词器文案')
    tail = t[i:]
    j = tail.find('\n---\n')
    if j < 0:
        raise SystemExit('❌ 提词器区块后面找不到 --- 分隔')
    front = tail[:j]
    k = front.find('\n\n')                      # 标题行与其后正文之间
    prefix = front[:k + 2] if k >= 0 else front + '\n\n'
    new_tail = prefix + prompter + tail[j + 1:]

    old_body = front[k + 2:].strip() if k >= 0 else ''
    same = old_body.split() == prompter.strip().split()

    print(f'口播句数：{len(sentences)}　→ 分 {len(titles)} 段')

    if a.check:
        print('✅ 一致（无需重生成）' if same else '⚠️ 有差异（去掉 --check 即写入）')
        return

    io.open(a.md, 'w', encoding='utf-8').write(t[:i] + new_tail)
    print('✅ 提词器已重生成' + ('（内容与原来相同）' if same else ''))
    print('   段标题：')
    for x in titles:
        print(f'     —— 第 N 段拍（{x}）——')


if __name__ == '__main__':
    main()
