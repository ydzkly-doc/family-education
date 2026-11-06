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

def spoken_body(text):
    head = re.search(prompter.SPOKEN_HEAD, text, re.M)
    rest = text[head.end():]
    return rest[:prompter._cut_zone(rest)]

def prompter_body(text):
    head = re.search(prompter.PROM_HEAD, text, re.M)
    rest = text[head.end():]
    return rest[:prompter._cut_zone(rest)]

def core(text):
    return re.sub(r'[“”"]', '', text.strip().rstrip('。？！'))

def anchor_replace(text, old, new):
    if old not in text:
        print(f'已应用或跳过: {old}')
        return text
    return text.replace(old, new, 1)

# 仅校正旧上屏表中与现稿措辞不同的条目。
replacements = {
15: {'是累、是烦、是委屈，还是不知道该做什么？': '今天是累，是烦，是委屈，还是不知道该做什么？'},
17: {'找专业的人一起看。': '找专业的人一起看看。',
     '说明问题，不只在设备。': '手机出了卧室、人还在翻。',
     '别把闭眼躺着，也变成一项任务。': '就是把"闭眼躺着"也变成一项任务'},
19: {'这是我们家用过的，不是标准答案。': '依据当年的回忆整理，细节已经模糊。',
     '那张纸，长得像一份通知。': '父母那一栏，也得真兑现。'},
20: {'谈崩那一刻，谁的话都进不去。': '谈崩那一刻，谁的话都进不去，包括我。',
     '只递一句：“你先缓，我们待会儿再说”。': '你先缓，我们待会儿再说。'},
22: {'真正要补的，是做成一件事的那个感觉。': '真正要补的，不是题量。'},
26: {'别说，他就是手机成瘾。': '这话一出口，等于你先下了结论。'},
27: {'成年人随时找得到。': '有个成年人随时找得到。',
     '这四种，别都留给孩子自己。': '这道底线不能省。',
     '换成大人，也得这么小心。': '有个成年人随时找得到。'},
30: {'父母退一步，不是撤离。': '交还的意思，是我们少提醒一次。'},
31: {'一句你不值得信任，说出口很痛快。': '说出口很痛快。'},
}
for number in range(13, 33):
    path = list(ROOT.glob(f'{number:02d}_*/视频号文案_*.md'))[0]
    text = path.read_text(encoding='utf-8')
    for old, new in replacements.get(number, {}).items():
        text = anchor_replace(text, old, new)
    body = spoken_body(text)
    original = re.sub(r'\s+', '', body)
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    anchors = anchor_tool.anchors(anchor_tool.section(text, '三、上屏方案'))
    unresolved = []
    for kind, anchor in anchors:
        if anchor in lines:
            continue
        needle = core(anchor)
        matches = [i for i, line in enumerate(lines) if needle in core(line)]
        if len(matches) != 1:
            unresolved.append((kind, anchor))
            continue
        i = matches[0]
        line = lines[i]
        normalized = core(line)
        start = normalized.index(needle)
        end = start + len(needle)
        prefix = normalized[:start].rstrip('，：—— ')
        suffix = normalized[end:].lstrip('，；：—— ')
        replacement = [x for x in (prefix, core(anchor), suffix) if x]
        lines[i:i + 1] = replacement
    if unresolved:
        print(number, 'UNRESOLVED', unresolved)
        raise SystemExit(1)
    new_body = '\n\n' + '\n\n'.join(line if line[-1] in '。？！' else line + '。' for line in lines) + '\n\n'
    if re.sub(r'[\s。？！，；：—”“"、]', '', new_body) != re.sub(r'[\s。？！，；：—”“"、]', '', body):
        raise SystemExit(f'{number}: 口播文字发生变化，停止')
    text = text.replace(body, new_body, 1)
    path.write_text(text, encoding='utf-8')
    print(f'{number}: 全部锚点已对齐，口播文字未删改')

# 用旧提词器的段标题和段尾定位，仅调用正式生成器。
for number in range(13, 33):
    path = list(ROOT.glob(f'{number:02d}_*/视频号文案_*.md'))[0]
    text = path.read_text(encoding='utf-8')
    old = prompter_body(text)
    titles = re.findall(r'——第 \d+ 段拍（(.+?)）——', old)
    segments = re.split(r'——第 \d+ 段拍（.+?）——', old)[1:]
    sentences = prompter.extract_spoken(spoken_body(text))
    cuts = []
    cursor = 0
    for segment in segments[:-1]:
        source = re.sub(r'[\s【】/]', '', segment)
        tail = source[-70:]
        candidates = range(cursor, len(sentences))
        index = max(candidates, key=lambda i: SequenceMatcher(None, tail, re.sub(r'\s+', '', sentences[i])).ratio())
        cuts.append(sentences[index])
        cursor = index + 1
    if len(titles) != len(cuts) + 1:
        raise SystemExit(f'{number}: 分段数量异常')
    words = prompter.collect_marks(text)
    result, nline, nsent, over = prompter.build_prompter(sentences, cuts, titles, words)
    head = re.search(prompter.PROM_HEAD, text, re.M)
    rest = text[head.end():]
    end = prompter._cut_zone(rest)
    text = text[:head.end()] + '\n\n' + result + rest[end + 1:]
    path.write_text(text, encoding='utf-8')
    print(f'{number}: 提词器已生成，{len(titles)} 段，{nsent} 句')
