#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
从文案 MD 的「二、口播文案」自动生成「三、提词器文案」。

为什么要用它（2026-09-25 立）：
    提词器文案是口播的**派生物**——手写/手改必然与口播不同步
    （实战中一次比对就报出 6 处差异：改了口播、忘了改提词器）。
    所以：**口播改完，跑一次这个脚本即可**。

为什么还要「气口版」（2026-09-28 立）：
    素人对着提词器念，**行太长就会念成"背书"**——一行 40+ 字，眼球来回扫、气接不上，
    语流被切成电报节奏（用户实拍反馈"生硬"）。所以生成时做三件事：
      ① **折行＝意群**：**先按标点切块、再填满整行**，不是按字数机械切
         （机械切会把一个意群切碎："上一条我说，／想给那些／孩子还没出问题的家庭／说点话"）；
      ② **气口** `//`：行内停半拍；**行尾＝大换气**（行本身就是呼吸单位）；
      ③ **重读【】**：⭐ 重读词**直接取「四、上屏方案」里已经标好的标色词**
         —— 凡是作者已标过重点的地方，**都不该再要第二处标注**（一份数据两用）。

用法：
    PY="C:/Users/ZhuanZ/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
    "$PY" 工具脚本/gen_prompter.py "文案.md" \
        --cuts "第1段最后一句。||第2段最后一句。||第3段最后一句。" \
        --titles "第 1 段拍（说明）||第 2 段拍（说明）||第 3 段拍（说明）||第 4 段拍（说明）"

    # 只看差异、不写入
    "$PY" 工具脚本/gen_prompter.py "文案.md" --cuts ... --titles ... --check

    # 退路：不要气口与重读、整句一行（旧行为）
    "$PY" 工具脚本/gen_prompter.py "文案.md" ... --plain

    # 微调行宽（默认 20 字；行数太多就调大）
    "$PY" 工具脚本/gen_prompter.py "文案.md" ... --max-line 24

规则：
    · 抽取：读口播段 → 丢掉所有【方括号】提示行 → 按 。？！断句（跨行的短句会合并成一句）
    · ⚠️ **只排除【方括号】行**：口播区里 `>` 开头的 markdown 引用行会被**当成台词、原样带进提词器**
      → **口播区不要写 `>` 说明行**，要写就写到「## 二、口播文案」区块之外（2026-09-27 实测踩过：
      写在口播区的一行说明，整行出现在提词器第 1 段里，用户复制进 App 会连说明一起念）
    · 分段：`--cuts` 给「每段的最后一句」（用 || 分隔），段数 = cuts 数 + 1
    · 标题：`--titles` 给每段的说明，脚本自动补成 `——第 N 段拍（说明）——`
    · ⚠️ 生成后 `---` 前会留一个空行（否则 Markdown 会把它解析成二级标题）
    · ⚠️ **`--check` 比对时会先剥掉 `//` 与【】**——记号不算差异（否则永远显示"有差异"）
"""
import argparse
import io
import re
import sys

# ── 气口版参数 ──────────────────────────────────────────────
MAX_LINE = 20     # 一行的宽度上限（字）；调大→行数少、每行更长
MIN_LINE = 7      # 每行至少这么多字
BREATH_MIN = 16   # 行内达到这么多字才考虑标气口
BREATH_EDGE = 4   # 气口距行两端至少留这么多字
DASH = "\x01"     # 破折号占位符（处理完换回 ——）
PRIMARY = set("，；：！？。" + DASH)   # 主切点（可在其后折行）
SECOND = set("、")                    # 次切点（仅整块过宽时用）

# ── 区块定位（2026-10-03 放宽，配合「6 节精简模板」）──────────────
# 旧写法写死了 `## 二、口播文案` + 后面的 `---`；精简模板改成
# `## 一、口播文案`（不再用 --- 分隔）就会报"找不到区块"。现在：
#   · 编号任意（`一、`/`二、`/没有编号都认），只认标题里的「口播文案」四个字；
#   · 区块结束改为「先出现的 `\n---\n` 或下一个 #/##/### 标题」，与管道 `md_spec._section()` 同口径。
SPOKEN_HEAD = r'^##[ \t]*(?:[^\s、]{1,4}、)?[ \t]*口播文案[^\n]*$'
PROM_HEAD = r'^##[ \t]*(?:[^\s、]{1,4}、)?[ \t]*提词器文案[^\n]*$'


def _cut_zone(rest: str) -> int:
    """区块正文的结束位置（返回的偏移上是 `\\n` 字符）。

    判据取**先出现者**：独立一行的 `---` ／ 下一个 `#`/`##`/`###` 标题。
    调用方一律用 `rest[j + 1:]` 接回剩下的原文——两种判据下都成立。
    """
    cands = []
    a = rest.find('\n---\n')
    if a >= 0:
        cands.append(a)
    h = re.search(r'\n#{1,3}\s', rest)
    if h:
        cands.append(h.start())
    return min(cands) if cands else len(rest)


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


def collect_marks(md_text: str):
    """从「上屏方案」节抽标色词（＝作者已定好的重读词）。

    只认「X」标…这种写法（"标"紧跟引号），因此**不会误抓"挂在这句：「…」"**。
    ⚠️ 2026-10-03：**编号任意**（新 6 节模板是「三、上屏方案」）——
    原来写死 `## 四、上屏方案` 会**抽不到词 → 提词器一个【】都没有**（静默失效）。
    """
    m = re.search(r'^#{2,4}[^\n]*上屏方案[^\n]*\n(.*?)(?=\n#{2}\s|\n---\n|\Z)',
                  md_text, re.S | re.M)
    blk = m.group(1) if m else ''
    words = []
    # 逐行处理：只看 `→` 右侧含"标"的行，并把**该侧所有引号词**都收进来。
    # ⚠️ 2026-10-03：旧写法用 `[「X」]\s*标` 逐个匹配，遇到**连续两个标色词**
    #   （`“警示灯”“不是全部答案”标暖色加粗`）只会抓到紧邻"标"的最后一个 → 静默漏词。
    for line in blk.split("\n"):
        if "→" not in line:
            continue
        rhs = line.split("→", 1)[1]
        if "标" not in rhs:
            continue
        for mm in re.finditer(r'[「\u201c\u201d"]([^」\u201c\u201d"]{2,14})[」\u201c\u201d"]', rhs):
            w = mm.group(1).strip()
            if w and w not in words:
                words.append(w)
    return words


def tokenize(text: str):
    """按标点切块（标点跟在块尾）。过宽的块再用顿号细切。"""
    parts, cur = [], ''
    for ch in text:
        cur += ch
        if ch in PRIMARY:
            parts.append(cur)
            cur = ''
    if cur:
        parts.append(cur)
    out = []
    for p in parts:
        if len(p) <= MAX_LINE:
            out.append(p)
            continue
        sub, c2 = [], ''
        for ch in p:
            c2 += ch
            if ch in SECOND:
                sub.append(c2)
                c2 = ''
        if c2:
            sub.append(c2)
        out.extend(sub)
    return out


def last_break(s: str) -> int:
    for i in range(len(s) - 1, 0, -1):
        if s[i - 1] in PRIMARY or s[i - 1] in SECOND:
            return i
    return -1


def pack(tokens):
    """把块贪心拼成行（不超 MAX_LINE），末行过短就从上行挪块。

    ⚠️ 行以破折号结尾时**强制断行** —— 破折号本身就是"停一拍、转场"的记号，
       再往后拼会把下一个意群粘上来（实测：「把"不上学"拆成具体的坎——是起不来床，」）。
    """
    lines, cur = [], ''
    for tk in tokens:
        if not cur:
            cur = tk
        elif len(cur) + len(tk) <= MAX_LINE and not cur.endswith(DASH):
            cur += tk
        else:
            lines.append(cur)
            cur = tk
    if cur:
        lines.append(cur)
    while len(lines) >= 2 and len(lines[-1]) < MIN_LINE:
        prev = lines[-2]
        cut = last_break(prev)
        if cut <= 0 or len(prev[:cut]) < MIN_LINE:
            break
        lines[-1] = prev[cut:] + lines[-1]
        lines[-2] = prev[:cut]
    return lines


def add_breath(line: str) -> str:
    """行内气口：够长的行、最多一个，格式「，// 后面」。"""
    if len(line) < BREATH_MIN:
        return line
    for pool in ('，；', '、'):
        cands = [i + 1 for i, ch in enumerate(line)
                 if ch in pool and BREATH_EDGE <= i + 1 <= len(line) - BREATH_EDGE]
        if cands:
            mid = len(line) / 2.0
            cut = min(cands, key=lambda i: abs(i - mid))
            # 破折号后面不再标（`——` 本身就是停顿），否则会写成 `——// `
            if line[:cut].rstrip().endswith('—'):
                continue
            return line[:cut] + '// ' + line[cut:]
    return line


def mark_read(line: str, words) -> str:
    """给重读词加【】（长词优先，且**只在未标记区段里替换**）。

    ⚠️ 不能直接用 `str.replace`（2026-10-03 实测踩到）：
      标色词常常**互相包含**（本例："还愿意回来找我" ⊃ "回来找我"）——
      长词先被标成 `【还愿意回来找我】`，短词再在里面命中一次 →
      生成**嵌套标记** `【还愿意【回来找我】】`（念的时候会莫名多一次停顿）。
      → 修法：每次替换前先算出已有的 `【…】` 区间，**落在区间内的命中一律跳过**。
    """
    for w in sorted(words, key=len, reverse=True):
        spans = [(m.start(), m.end()) for m in re.finditer(r'【[^】]*】', line)]

        def inside(i: int) -> bool:
            return any(s < i < e for s, e in spans)

        res, i = '', 0
        while True:
            j = line.find(w, i)
            if j < 0:
                res += line[i:]
                break
            if inside(j) or inside(j + len(w) - 1):
                res += line[i:j + 1]
                i = j + 1
                continue
            res += line[i:j] + '【' + w + '】'
            i = j + len(w)
        line = res
    return line


def render(sentence: str, words=(), plain=False):
    """一句 → 若干行"""
    if plain:
        return [sentence.strip()]
    text = sentence.strip().replace('——', DASH)
    lines = [add_breath(x) for x in pack(tokenize(text))]
    out = []
    for x in lines:
        x = x.replace(DASH, '——')
        out.append(mark_read(x, words) if words else x)
    return out


def strip_marks(s: str) -> str:
    """剥掉记号（`--check` 比对用）：记号不算差异"""
    s = s.replace('//', '').replace('【', '').replace('】', '')
    return re.sub(r'\s+', '', s)


def build_prompter(sentences, cuts, titles, words=(), plain=False):
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

    out, nline, over = [], 0, []
    for i, (t, s) in enumerate(zip(titles, seg), 1):
        out.append(f'——第 {i} 段拍（{t}）——')
        for sent in s:
            for line in render(sent, words, plain):
                nline += 1
                out.append(line)
                if len(strip_marks(line)) > MAX_LINE:
                    over.append(line)
        out.append('')
    plain_text = '\n'.join(out).rstrip() + '\n\n'   # ⚠️ 末尾留空行，保住后面的 ---
    return plain_text, nline, len(sentences), over


def _selftest():
    """回归锁：折行／气口／破折号／重读的六条硬规则"""
    ok = 0

    def chk(cond, msg):
        nonlocal ok
        if cond:
            ok += 1
            print(f'  ✅ {msg}')
        else:
            print(f'  ❌ {msg}')
            sys.exit(1)

    # ①② 折行不超宽、不产生空行
    s = '可孩子的身体和情绪、学校里的情况都还没看清，就只围着返校使劲，真正的坎会被一直挡在后面。'
    lines = pack(tokenize(s))
    chk(all(0 < len(l) <= MAX_LINE for l in lines), f'折行不超宽 {[len(l) for l in lines]}')
    chk(len(lines) >= 2, f'长句确实被折开了（{len(lines)} 行）')

    # ③ 破折号整体不拆（行首/行尾不得只剩一个 —）
    d = '把"不上学"拆成具体的坎——是起不来床，是路上，是校门，是教室，还是某一节课、某一段关系？'
    dl = render(d)
    chk(not any(l.startswith('—') or (l.endswith('—') and not l.endswith('——')) for l in dl),
        f'破折号不被拆开（{dl}）')

    # ④ 破折号后强制断行
    chk(any(l.endswith('——') for l in dl), '破折号落在行尾（其后强制断行）')

    # ⑤ 气口格式：`//` 前面必须紧跟标点，且每行最多一个
    b = add_breath('我呢，下班不想回家；回了家也不说话，')
    chk('// ' in b and b[b.index('// ') - 1] in '，；、', f'气口格式「，// 后面」（{b}）')
    chk(all(l.count('//') <= 1 for l in render(s)), '每行最多一个气口')

    # ⑥ 短行不加气口（14 字以下）
    chk('//' not in add_breath('更多方法，我写在公众号里了。'), '短行不加气口')

    # ⑦ 重读只标命中词，不误伤
    m = mark_read('我不是不管孩子，我是往反方向使劲。', ['往反方向使劲'])
    chk(m == '我不是不管孩子，我是【往反方向使劲】。', f'重读标记正确（{m}）')
    chk(mark_read('跟我无关的一句。', ['往反方向使劲']) == '跟我无关的一句。', '未命中的句子不动')

    # ⑧ 比对剥记号
    chk(strip_marks('一直【各拉各的车】。// ') == '一直各拉各的车。', '--check 的剥记号正确')

    # ⑨ 标色词抽取只认「X」标…，不抓"挂在这句：「…」"（标色词按 ≥2 字计）
    w = collect_marks('## 四、上屏方案\n1. 「甲乙句」 → "甲乙"标暖色\n   - 挂在这句：「丙丁句」\n')
    chk(w == ['甲乙'], f'标色词抽取（{"、".join(w)}）')

    # ⑩ 互相包含的标色词**不产生嵌套标记**（2026-10-03 实测：`【还愿意【回来找我】】`）
    n = mark_read('是他不同意之后，还愿意回来找我说话。', ['回来找我', '还愿意回来找我', '不同意'])
    chk(n == '是他【不同意】之后，【还愿意回来找我】说话。', f'标色词嵌套已消除（{n}）')
    chk('【' not in n.replace('【不同意】', '').replace('【还愿意回来找我】', ''), '标记不重叠')

    print(f'\n✅ gen_prompter 自检：{ok} 项全部通过')


def main():
    global MAX_LINE          # ⚠️ 必须在任何引用 MAX_LINE 之前声明
    ap = argparse.ArgumentParser()
    ap.add_argument('md', nargs='?', default='', help='文案 MD 路径')
    ap.add_argument('--cuts', default='', help='每段最后一句，用 || 分隔')
    ap.add_argument('--titles', default='', help='每段说明（不含"第 N 段拍"），用 || 分隔')
    ap.add_argument('--check', action='store_true', help='只比对，不写入')
    ap.add_argument('--plain', action='store_true',
                    help='退路：整句一行、不加气口与重读（旧行为）')
    ap.add_argument('--no-mark', action='store_true', help='不加重读【】（仍折行、仍加气口）')
    ap.add_argument('--max-line', type=int, default=MAX_LINE,
                    help=f'行宽上限（字），默认 {MAX_LINE}；行数太多就调大')
    ap.add_argument('--selftest', action='store_true', help='跑回归自检（不需要任何素材）')
    a = ap.parse_args()

    if a.selftest:
        _selftest()
        return

    MAX_LINE = a.max_line

    if not a.md or not a.cuts or not a.titles:
        raise SystemExit('❌ 用法：gen_prompter.py <文案.md> --cuts "…" --titles "…"'
                         '（或 --selftest 跑自检）')

    t = io.open(a.md, encoding='utf-8').read()

    mh = re.search(SPOKEN_HEAD, t, re.M)
    if not mh:
        raise SystemExit('❌ 找不到「## …口播文案」区块（标题里必须有「口播文案」四个字）')
    _rest = t[mh.end():]
    sentences = extract_spoken(_rest[:_cut_zone(_rest)])

    words = [] if (a.plain or a.no_mark) else collect_marks(t)

    cuts = [c for c in a.cuts.split('||') if c.strip()]
    titles = [x.strip() for x in a.titles.split('||') if x.strip()]
    prompter, nline, nsent, over = build_prompter(sentences, cuts, titles, words, a.plain)

    # 定位「提词器文案」区块（标题行保留，正文整段替换）
    ph = re.search(PROM_HEAD, t, re.M)
    if not ph:
        raise SystemExit('❌ 找不到「## …提词器文案」区块')
    head_line = t[ph.start():ph.end()]
    tail = t[ph.end():]
    j = _cut_zone(tail)
    front = tail[:j]
    k = front.find('\n\n')                      # 标题行与其后正文之间
    prefix = head_line + (front[:k + 2] if k >= 0 else front + '\n\n')
    new_tail = prefix + prompter + tail[j + 1:]

    old_body = front[k + 2:].strip() if k >= 0 else ''
    # ⚠️ 分两级比对，否则会误判"不用重生成"：
    #    · 文字内容（剥掉记号与空白后）——检验提词器与口播是否同步
    #    · 原始排版（连换行一起比）——检验排版是不是最新版（气口版改的就是排版！）
    same_text = strip_marks(old_body) == strip_marks(prompter)
    same_raw = old_body.split() == prompter.strip().split()

    print(f'口播句数：{nsent}　→ 分 {len(titles)} 段　→ 提词器 {nline} 行'
          + ('' if a.plain else f'（气口版，行宽上限 {MAX_LINE}）'))
    if words:
        print(f'重读词 {len(words)} 个（取自「上屏方案」节的标色词）：{"、".join(words)}')
    if over:
        print(f'⚠️ {len(over)} 行超过行宽 {MAX_LINE} 字 —— 多半是**没有标点的长串**，折不开是正常的，肉眼确认一下：')
        for l in over[:5]:
            print(f'     · {l}')

    if a.check:
        if same_raw:
            print('✅ 一致（文字与排版都是最新）')
        elif same_text:
            print('⚠️ 文字一致，但**排版是旧版**（去掉 --check 即更新为气口版）')
        else:
            print('⚠️ **文字内容有差异**（去掉 --check 即写入）')
        return

    io.open(a.md, 'w', encoding='utf-8').write(t[:ph.start()] + new_tail)
    print('✅ 提词器已重生成' + ('（内容与原来相同）' if same_text else ''))
    if not a.plain:
        print('   记号：行尾＝大换气　// ＝行内停半拍　【】＝重读')
    print('   段标题：')
    for x in titles:
        print(f'     —— 第 N 段拍（{x}）——')


if __name__ == '__main__':
    main()
