# -*- coding: utf-8 -*-
from pathlib import Path
import importlib.util
import re
import sys
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
sys.path.insert(0, str(Path.home() / '.workbuddy/skills/ffmpeg-vertical-video-pipeline/scripts'))
import md_spec

def split_spoken(text):
    head = re.search(prompter.SPOKEN_HEAD, text, re.M)
    rest = text[head.end():]
    return rest[:prompter._cut_zone(rest)]

def normalize(text):
    return re.sub(r'[\s【】/]', '', text)

for number in range(13, 33):
    paths = list(ROOT.glob(f'{number:02d}_*/视频号文案_*.md'))
    if len(paths) != 1:
        raise SystemExit(f'{number}: 文件数量异常')
    path = paths[0]
    text = path.read_text(encoding='utf-8')
    body = split_spoken(text)
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    spoken = prompter.extract_spoken(body)
    anchors = anchor_tool.anchors(anchor_tool.section(text, '三、上屏方案'))
    missing = []
    embedded = []
    for kind, anchor in anchors:
        if anchor in lines:
            continue
        containing = [line for line in lines if anchor in line]
        if len(containing) == 1:
            embedded.append(anchor)
        else:
            missing.append((kind, anchor))
    # 只拆行，不删除、不新增任何口播文字。
    for anchor in embedded:
        index = next(i for i, line in enumerate(lines) if anchor in line)
        line = lines[index]
        start = line.index(anchor)
        before, after = line[:start].strip(), line[start + len(anchor):].strip()
        replacement = [x for x in (before, anchor, after) if x]
        lines[index:index + 1] = replacement
    new_body = '\n\n' + '\n\n'.join(lines) + '\n\n'
    text = text.replace(body, new_body, 1)
    path.write_text(text, encoding='utf-8')
    print(f'{number}: 口播 {len(normalize(body))} 字；拆行 {len(embedded)}；缺失锚点 {len(missing)}')
    for kind, anchor in missing:
        best = max(spoken, key=lambda sent: SequenceMatcher(None, anchor, sent).ratio())
        score = SequenceMatcher(None, anchor, best).ratio()
        print(f'  MISSING [{kind}] {anchor}\n  CANDIDATE {best} ({score:.2f})')
