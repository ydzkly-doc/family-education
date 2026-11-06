# -*- coding: utf-8 -*-
from pathlib import Path
import importlib.util
import re
from difflib import SequenceMatcher
ROOT = Path(__file__).resolve().parent
TOOL = ROOT.parents[2] / '工具脚本' / 'gen_prompter.py'
spec = importlib.util.spec_from_file_location('gen_prompter', TOOL)
gp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gp)

def section(text, pattern):
    head = re.search(pattern, text, re.M)
    rest = text[head.end():]
    return rest[:gp._cut_zone(rest)]

for number in range(22, 33):
    path = list(ROOT.glob(f'{number:02d}_*/视频号文案_*.md'))[0]
    text = path.read_text(encoding='utf-8')
    spoken = section(text, gp.SPOKEN_HEAD)
    original_spoken = spoken
    old = section(text, gp.PROM_HEAD)
    titles = re.findall(r'——第 \d+ 段拍（(.+?)）——', old)
    segments = re.split(r'——第 \d+ 段拍（.+?）——', old)[1:]
    sentences = [re.sub(r'\*+', '', line.strip()) for line in spoken.splitlines() if line.strip()]
    if number == 21:
        joined = ''.join(sentences)
        first = '你可记住了，“但你也有错”，这半句，最扣分。'
        if first not in joined:
            first = first.replace('“', '"').replace('”', '"')
        second = '而且只说这一件事，不翻旧账。'
        end1 = joined.index(first) + len(first)
        end2 = joined.index(second) + len(second)
        sentences = [joined[:end1 + 1], joined[end1 + 1:end2 + 1], joined[end2 + 1:]]
        print('21 分段字数', [len(part) for part in sentences], '总字数', len(joined))
    cuts = []
    cursor = 0
    for segment in ([] if number == 21 else segments[:-1]):
        wanted = gp.strip_marks(segment)
        best = None
        for end in range(cursor + 1, len(sentences) + 1):
            candidate = gp.strip_marks(''.join(sentences[cursor:end]))
            score = SequenceMatcher(None, wanted, candidate).ratio()
            if best is None or score > best[0]:
                best = score, end
        score, end = best
        if score < 0.55:
            # 旧提词器是压缩版，只用于确认主题顺序；这里保留口播自然段边界。
            end = cursor + 1
            while end < len(sentences):
                candidate = gp.strip_marks(''.join(sentences[cursor:end + 1]))
                if SequenceMatcher(None, wanted, candidate).ratio() <= score:
                    break
                end += 1
        cuts.append(sentences[end - 1])
        cursor = end
    if number == 21:
        cuts = [sentences[0], sentences[1]]
        cursor = 2
    result, _, _, _ = gp.build_prompter(sentences, cuts, titles, gp.collect_marks(text))
    head = re.search(gp.PROM_HEAD, text, re.M)
    rest = text[head.end():]
    end = gp._cut_zone(rest)
    updated = text[:head.end()] + '\n\n' + result + rest[end + 1:]
    if section(updated, gp.SPOKEN_HEAD) != original_spoken:
        raise SystemExit(f'{number}: 口播保护校验失败，停止写入')
    path.write_text(updated, encoding='utf-8')
    print(f'{number}: 提词器 {len(titles)} 段已同步；口播未改动')
