# -*- coding: utf-8 -*-
from pathlib import Path
import importlib.util
import re
from difflib import SequenceMatcher
ROOT = Path(__file__).resolve().parent
TOOLS = ROOT.parents[2] / '工具脚本'
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
anchor_tool = load('anchors', TOOLS / 'video_script_anchor_check.py')
prompter = load('prompter', TOOLS / 'gen_prompter.py')
def body(text, pattern):
    head = re.search(pattern, text, re.M)
    rest = text[head.end():]
    return rest[:prompter._cut_zone(rest)]
# 旧锚点的文字校准，只动上屏表。
changes = {
15: {'是累、是烦、是委屈，还是不知道该做什么？': '今天是累，是烦，是委屈，还是不知道该做什么？'},
17: {'说明问题，不只在设备。': '手机出了卧室、人还在翻。', '找专业的人一起看。': '找专业的人一起看看。', '别把闭眼躺着，也变成一项任务。': '就是把"闭眼躺着"也变成一项任务。'},
18: {'你就不能管住自己？': '你就不能管住自己吗？'},
19: {'这是我们家用过的，不是标准答案。': '依据当年的回忆整理，细节已经模糊。', '那张纸，长得像一份通知。': '父母那一栏，也得真兑现。'},
20: {'谈崩那一刻，谁的话都进不去。': '谈崩那一刻，谁的话都进不去，包括我。', '只递一句：“你先缓，我们待会儿再说”。': '只递一句："你先缓，我们待会儿再说。"'},
22: {'真正要补的，是做成一件事的那个感觉。': '真正要补的，不是题量。'},
26: {'别说，他就是手机成瘾。': '这话一出口，等于你先下了结论。'},
27: {'这四种，别都留给孩子自己。': '这道底线不能省。', '成年人随时找得到。': '有个成年人随时找得到。'},
31: {'一句你不值得信任，说出口很痛快。': '说出口很痛快。'},
}
for number in range(13, 33):
    path = list(ROOT.glob(f'{number:02d}_*/视频号文案_*.md'))[0]
    text = path.read_text(encoding='utf-8')
    for old, new in changes.get(number, {}).items():
        if old in text:
            text = text.replace(old, new)
    spoken = body(text, prompter.SPOKEN_HEAD)
    lines = [line.strip() for line in spoken.splitlines() if line.strip()]
    anchors = anchor_tool.anchors(anchor_tool.section(text, '三、上屏方案'))
    for kind, anchor in anchors:
        if anchor in lines:
            continue
        # 保留原行字符；锚点缺少末尾标点时只插入该标点。
        candidates = []
        needle = anchor.rstrip('。？！')
        for i, line in enumerate(lines):
            start = line.find(needle)
            if start >= 0:
                candidates.append((i, start))
        if len(candidates) != 1:
            print(number, '未匹配', anchor)
            continue
        i, start = candidates[0]
        line = lines[i]
        end = start + len(needle)
        actual = line[start:end]
        if actual != anchor:
            if line[end:end + 1] in '。？！':
                end += 1
            else:
                line = line[:end] + anchor[-1] + line[end:]
                end += 1
        exact = line[start:end]
        before, after = line[:start].strip(), line[end:].strip()
        lines[i:i + 1] = [x for x in (before, exact, after) if x]
    new_spoken = '\n\n' + '\n\n'.join(lines) + '\n\n'
    # 除新插入的句末标点外，逐字保留。
    if re.sub(r'[。？！]', '', new_spoken) != re.sub(r'[。？！]', '', spoken):
        raise SystemExit(f'{number}: 口播字符保护失败')
    text = text.replace(spoken, new_spoken, 1)
    path.write_text(text, encoding='utf-8')
    print(number, '断行完成')

for number in range(13, 33):
    path = list(ROOT.glob(f'{number:02d}_*/视频号文案_*.md'))[0]
    text = path.read_text(encoding='utf-8')
    old = body(text, prompter.PROM_HEAD)
    titles = re.findall(r'——第 \d+ 段拍（(.+?)）——', old)
    segments = re.split(r'——第 \d+ 段拍（.+?）——', old)[1:]
    sentences = prompter.extract_spoken(body(text, prompter.SPOKEN_HEAD))
    cuts, cursor = [], 0
    for segment in segments[:-1]:
        tail = prompter.strip_marks(segment)[-70:]
        candidates = range(cursor, len(sentences))
        if not candidates:
            raise SystemExit(f'{number}: 分段越界')
        index = max(candidates, key=lambda i: SequenceMatcher(None, tail, sentences[i]).ratio())
        cuts.append(sentences[index])
        cursor = index + 1
    result, _, _, _ = prompter.build_prompter(sentences, cuts, titles, prompter.collect_marks(text))
    head = re.search(prompter.PROM_HEAD, text, re.M)
    rest = text[head.end():]
    end = prompter._cut_zone(rest)
    text = text[:head.end()] + '\n\n' + result + rest[end + 1:]
    path.write_text(text, encoding='utf-8')
    print(number, '提词器完成')
