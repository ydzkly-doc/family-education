# -*- coding: utf-8 -*-
"""卡片密度预估（通用版）· 渲染前拦截

⭐ 用途：写配置后、渲染前跑，在动手前拦下过密/过稀卡，避免渲完返工。
   密度超标（SOP 案例 C19）已连发 4 次，根因都是"执行时偏离设计稿"。

⭐ 判据（SOP 14-card-writing.md 2.3 / 15-card-visual.md 11.3）
   目标带 62%–68% ｜ 红线 > 70% 必须处理 ｜ 下限 < 58% 补信息

⭐ 密度 = 内容块总高 / 可用区高
   公式逐一对齐所传渲染器的实现（不是估算），覆盖 content/compare/timeline/quad 四种卡型。

用法：
   python 卡片密度预估_density.py --base "<卡片文章目录>" [篇号 …]
   python 卡片密度预估_density.py --base "D:/…/父母做到这点孩子会有惊人改变/公众号文章/卡片文章" 1 2 3
选项：
   --render  渲染器文件名（默认 卡片文章渲染_card_render.py）
   --all     扫描该目录下全部存在的配置
"""
import sys, os, json, argparse, importlib.util

sys.stdout.reconfigure(encoding='utf-8')

ap = argparse.ArgumentParser()
ap.add_argument('--base', required=True, help='卡片文章目录（含 脚本/ 与 _过程文件/）')
ap.add_argument('--render', default='卡片文章渲染_card_render.py')
ap.add_argument('--all', action='store_true')
ap.add_argument('nums', nargs='*', type=int)
A = ap.parse_args()

B = A.base
RENDER = os.path.join(B, '脚本', A.render)
if not os.path.exists(RENDER):
    print('❌ 渲染器不存在：%s' % RENDER); sys.exit(2)

spec = importlib.util.spec_from_file_location('R', RENDER)
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)

from PIL import Image, ImageDraw
_d = ImageDraw.Draw(Image.new('RGB', (R.W, R.H)))

W, H, MARGIN = R.W, R.H, R.MARGIN
AREA_TOP, AREA_BOT = 132, H - MARGIN - 26
AVAIL = AREA_BOT - AREA_TOP


def total_of(card, cfg):
    """按卡型复现渲染器的 total（内容块总高）"""
    sc = cfg.get('content_scale', 1.0)
    t = card.get('type')

    if t == 'content':
        X = MARGIN + 52
        MW = W - X - MARGIN
        f_topic = R.font(int(32 * sc))
        f_head = R.font(int(60 * sc), True)
        f_body = R.font(int(40 * sc))
        head_h = int(f_head.size * 1.34) * len(R.wrap(_d, card['head'], f_head, MW))
        body_h = R.para_h(_d, card['paras'], f_body, MW)
        return f_topic.size + 28 + head_h + 40 + 30 + body_h, \
               sum(len(p) for p in card['paras'])

    if t == 'compare':
        f_topic, f_h, f_b = R.font(32), R.font(56, True), R.font(40)
        pad, PADIN = MARGIN, 48
        heights = []
        for title, body in card['rows']:
            n = len(R.wrap(_d, body, f_b, W - pad * 2 - PADIN * 2))
            # 行距须与渲染器 compare 分支一致（见脚本内 1.66 / gap）
            heights.append(PADIN * 2 + f_h.size + 30 + int(f_b.size * 1.66) * n)
        total = f_topic.size + 28 + sum(heights) + 56 * (len(card['rows']) - 1)
        return total, sum(len(b) for _, b in card['rows'])

    if t == 'timeline':
        X = MARGIN + 82
        MW = W - X - MARGIN
        f_topic, f_head = R.font(32), R.font(54, True)
        f_t, f_b = R.font(50, True), R.font(38)
        head_lines = R.wrap(_d, card['head'], f_head, MW)
        _h = f_topic.size + 24 + int(f_head.size * 1.34) * len(head_lines) + 50
        for _tt, _body in card['nodes']:
            # ⚠️ 节点间距须与渲染器 timeline 分支一致（当前 64）
            _h += f_t.size + 20 + int(f_b.size * 1.64) * len(R.wrap(_d, _body, f_b, MW)) + 64
        return _h - 64, sum(len(b) for _, b in card['nodes'])

    if t == 'quad':
        f_topic, f_head = R.font(32), R.font(54, True)
        f_q, f_b = R.font(50, True), R.font(35)
        MW = W - MARGIN * 2
        head_lines = R.wrap(_d, card['head'], f_head, MW)
        gap, card_w, pad_in = 48, ((W - MARGIN * 2) - 48) // 2, 52
        inner_w = card_w - pad_in * 2
        cell_h = 0
        for q in card['quads'][:4]:
            hh = f_q.size + 22 + int(f_b.size * 1.60) * len(R.wrap(_d, q['d'], f_b, inner_w))
            cell_h = max(cell_h, hh)
        cell_h += pad_in * 2
        total = f_topic.size + 26 + int(f_head.size * 1.34) * len(head_lines) + 52 + cell_h * 2 + gap
        return total, sum(len(q['d']) for q in card['quads'])

    return None, 0


nums = A.nums
if A.all or not nums:
    nums = []
    for f in sorted(os.listdir(os.path.join(B, '脚本'))):
        if f.endswith('_卡片配置.json'):
            nums.append(int(f[1:3]))
if not nums:
    print('❌ 未找到任何配置'); sys.exit(2)

print('渲染器：%s' % A.render)
print('可用区 %d ~ %d ｜ 高 %d px' % (AREA_TOP, AREA_BOT, AVAIL))
print('目标带 62–68%% → 块高 %d ~ %d px ｜ 红线 70%% = %d px\n'
      % (AVAIL * .62, AVAIL * .68, AVAIL * .70))

stat = {'ok': 0, 'high': 0, 'low': 0, 'over': 0}
for n in nums:
    p = os.path.join(B, '脚本', '第%02d篇_卡片配置.json' % n)
    if not os.path.exists(p):
        print('第%d篇：配置不存在，跳过\n' % n)
        continue
    cfg = json.loads(open(p, encoding='utf-8').read())
    print('═══ 第%d篇 ═══' % n)
    for c in cfg['cards']:
        total, nchar = total_of(c, cfg)
        if total is None:
            print('  %-26s %-9s （封面/收尾，不计内容密度）'
                  % (c['file'][:24], c.get('type', '')))
            continue
        dens = total / AVAIL
        if .62 <= dens <= .68:
            flag, k = '✅ 目标带', 'ok'
        elif dens > .70:
            flag, k = '✖ 破红线（>70%）', 'over'
        elif dens > .68:
            flag, k = '⚠️ 偏高', 'high'
        elif dens >= .58:
            flag, k = '⚠️ 偏低', 'low'
        else:
            flag, k = '⚠️ 过稀', 'low'
        stat[k] += 1
        print('  %-26s %-9s 字 %3d ｜ 块高 %4d ｜ 密度 %.1f%%  %s'
              % (c['file'][:24], c.get('type', ''), nchar, total, dens * 100, flag))
    print()

print('统计：目标带 %d ｜ 偏高 %d ｜ 偏低/过稀 %d ｜ 破红线 %d'
      % (stat['ok'], stat['high'], stat['low'], stat['over']))
sys.exit(0 if stat['ok'] == stat['ok'] + stat['high'] + stat['low'] + stat['over'] else 1)
