# -*- coding: utf-8 -*-
"""封面卡 16:9 安全区 + 顶部标注对比度 · 白盒核验（通用版）

⭐ 为什么用白盒（读渲染器 BOXES）而不是图像法：
   底图卡上用"亮度/颜色找文字"必然误报——底图暗化后暖光与浅色文字色值接近
   （SOP 案例 C18 记录过）。渲染器本来就用 BOXES 做断言，直接读它最可靠。
   本脚本只调渲染函数、不写任何文件。

⭐ 16:9 安全区 = (1656 − 1242×9/16)/2 ≈ 479 ~ 1177
   信息流与转发会从大图中心裁方形显示，关键内容必须落在带内。

用法：
   python 封面卡安全区核验_白盒.py --base "<卡片文章目录>" [篇号 …]
"""
import sys, os, json, argparse, importlib.util

sys.stdout.reconfigure(encoding='utf-8')

ap = argparse.ArgumentParser()
ap.add_argument('--base', required=True)
ap.add_argument('--render', default='卡片文章渲染_card_render.py')
ap.add_argument('--all', action='store_true')
ap.add_argument('nums', nargs='*', type=int)
A = ap.parse_args()

B = A.base
spec = importlib.util.spec_from_file_location('R', os.path.join(B, '脚本', A.render))
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)

W, H = R.W, R.H
SAFE_TOP = int((H - W * 9 / 16) / 2)
SAFE_BOT = int((H + W * 9 / 16) / 2)

nums = A.nums
if A.all or not nums:
    nums = sorted(int(f[1:3]) for f in os.listdir(os.path.join(B, '脚本'))
                  if f.endswith('_卡片配置.json'))
if not nums:
    print('❌ 未找到配置'); sys.exit(2)

print('16:9 安全区 y %d ~ %d ｜ 渲染器 %s\n' % (SAFE_TOP, SAFE_BOT, A.render))
allok = True
for n in nums:
    p = os.path.join(B, '脚本', '第%02d篇_卡片配置.json' % n)
    if not os.path.exists(p):
        continue
    CFG = json.loads(open(p, encoding='utf-8').read())
    R.CFG = CFG
    if CFG.get('notes'):
        R.NOTES = CFG['notes']
    R.BG_DIR = CFG.get('bg') or os.path.join(B, '_过程文件', '底图成品')
    R.CUR_NOTE = None

    cover = CFG.get('cover') or {}
    if not cover.get('bg'):
        print('第%d篇：无封面配置，跳过' % n); continue

    R.BOXES.clear(); R.CONTAINERS.clear()
    R.CUR_NOTE = cover.get('note')
    R.cover_card()
    boxes = list(R.BOXES)

    labels, content = boxes[:2], boxes[2:]
    print('═══ 第%d篇 封面卡 ═══' % n)
    if content:
        y0 = min(b[1] for b in content); y1 = max(b[3] for b in content)
        ok = y0 >= SAFE_TOP and y1 <= SAFE_BOT
        allok &= ok
        print('  主文案 y %4d~%4d ｜ %s%s'
              % (y0, y1, '✅ 在带内' if ok else '✖ 出界',
                 '' if ok else '（上溢 %d / 下溢 %d）'
                 % (max(0, SAFE_TOP - y0), max(0, y1 - SAFE_BOT))))
    # 顶部标注（P0）——第一条系列行、第二条逐张标注
    for i, b in enumerate(labels):
        tag = '系列行' if i == 0 else '标注行(P0)'
        ins = SAFE_TOP <= b[1]
        print('  %-12s y %4d~%4d  %s' % (tag, b[1], b[3],
                                          '✅' if ins else '✖ 在安全区上方（裁切后不可见）'))
    print()

print('判定：%s' % ('✅ 全部封面卡主文案在 16:9 安全区内' if allok else '❌ 有封面卡出界'))
sys.exit(0 if allok else 1)
