# -*- coding: utf-8 -*-
from pathlib import Path
import importlib.util
import re
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
for number in range(13, 33):
    path = list(ROOT.glob(f'{number:02d}_*/视频号文案_*.md'))[0]
    text = path.read_text(encoding='utf-8')
    spoken = body(text, prompter.SPOKEN_HEAD)
    prompt = body(text, prompter.PROM_HEAD)
    s = prompter.extract_spoken(spoken)
    p = prompter.extract_spoken(prompt)
    # 标题不入提词器正文，对比文字。
    prompt_clean = re.sub(r'——第 \d+ 段拍（.+?）——', '', prompt)
    identical = prompter.strip_marks(spoken) == prompter.strip_marks(prompt_clean)
    spoken_lines = [line.strip() for line in spoken.splitlines() if line.strip()]
    missing = [a for kind, a in anchor_tool.anchors(anchor_tool.section(text, '三、上屏方案')) if a not in spoken_lines]
    first = next(line.strip() for line in spoken.splitlines() if line.strip())
    count = len(re.sub(r'\s+', '', spoken))
    print(f'{number}: {count}字；双稿={identical}；锚点缺失={len(missing)}；开场={first}')
    if not identical:
        print('  SPOKEN', prompter.strip_marks(spoken)[:100])
        print('  PROMPT', prompter.strip_marks(prompt_clean)[:100])
