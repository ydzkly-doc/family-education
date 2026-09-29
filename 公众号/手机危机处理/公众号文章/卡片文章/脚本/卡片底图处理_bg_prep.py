# -*- coding: utf-8 -*-
"""卡片底图预处理（通用版 · 参数化）
去水印 → 3:4 → 保护性暗化 → 柔化 → 顶部压字区 → 统一尺寸 → 自检

用法：
  python 卡片底图处理_bg_prep.py \
      --base "<系列>/公众号文章/卡片文章" \
      --cover <封面底图文件名或路径> \
      --closing <收尾底图文件名或路径> \
      --prefix <篇号前缀，如 第14篇>

说明：
  - 底图默认在 <base>/_过程文件/底图/ 下；也可直接给绝对路径
  - 输出到 <base>/_过程文件/底图成品/，文件名带篇号前缀（如 第14篇_封面卡_底图.png）
    ⛔ 必须带前缀：否则下一篇处理会覆盖上一篇的成品（2026-09-15 踩过）
  - 每篇只需 2 张 AI 底图（封面卡 + 收尾卡），内容卡用纯色底
"""
import sys, os, argparse
sys.stdout.reconfigure(encoding='utf-8')
from PIL import Image, ImageFilter
import numpy as np

W, H = 1242, 1656          # 目标尺寸（全资产统一）
MAX_UPSCALE = 1.30         # 放大倍数上限（保护锐度）


def detect_watermark(a, h, w, strict=True):
    """检测水印（浅色小字块，靠右下、宽度占比小、对比高）。
    自然图像里的台面高光/瓷碟边缘会误触发 → 故缩窄检测带并提高对比门槛。
    最终以人工目检为准。"""
    frac = 0.94 if strict else 0.86
    y0 = int(h * frac)
    reg = a[y0:, :]
    rows = reg.mean(axis=1)
    if len(rows) < 4:
        return (None, None)
    base = float(np.percentile(rows, 30))
    hits = []
    for i, v in enumerate(rows):
        if v <= base + 14:
            continue
        line = reg[i]
        bright = line > (line.mean() + 18)
        if bright.sum() < 8:
            continue
        xs = np.where(bright)[0]
        if (xs > w * 0.60).mean() >= 0.80:      # 亮像素集中在右侧 → 更像水印
            hits.append(y0 + i)
    if not hits:
        return (None, None)
    return (hits[0], hits[-1])


def darken_top(im, strength=0.55, coverage=0.60, color='#1c1410'):
    """顶部渐变压字区：从顶到底由深到透明，让大字可读。"""
    W_, H_ = im.size
    m = Image.new('L', (1, H_), 0)
    px = m.load()
    end = max(1, int(H_ * coverage))
    for y in range(H_):
        if y < end:
            t = 1 - (y / end)
            px[0, y] = int(255 * strength * (t ** 0.85))
        else:
            px[0, y] = 0
    return Image.composite(Image.new('RGB', (W_, H_), color), im, m.resize((W_, H_)))


def prep(src, dst, out_name, veil_a, veil_c, top_dark=0.0, blur=1.1, cut_override=0):
    im = Image.open(src).convert('RGB')
    w, h = im.size
    print('\n▌ %s' % os.path.basename(src)[:64])
    print('  原图 %dx%d 比例 %.4f' % (w, h, w / h))

    # ① 去水印：顶锚裁到 3:4 高；若水印落在裁切线内则继续下裁
    need_h = int(round(w * 4 / 3))
    g = np.array(im.convert('L')).astype(float)
    wy0, wy1 = detect_watermark(g, h, w, strict=False)
    if wy0:
        print('  检出水印 y=%d~%d' % (wy0, wy1))
    cut_h = min(need_h, h)
    # ⭐ 2026-09-19 修正：原判据 `wy1 >= cut_h` 只在"水印下缘超出裁切线"时才下裁，
    #    但水印常整段落在裁切线*之上* → 漏检残留。
    #    正确判据：只要水印起点 wy0 落在裁切线内，就裁到 wy0 之上。
    if wy0 and wy0 < cut_h:
        cut_h = wy0 - 8
        print('  ⚠️ 水印落在裁切线内 → 下裁至 y=%d' % cut_h)
    # ⭐ 手动覆盖：AI 水印位置每批可能不同，目检发现残留时用 --cut-bottom 硬裁
    if cut_override and cut_override < h:
        cut_h = cut_override
        print('  ⚙️ 手动指定裁切高度 y=%d' % cut_h)
    # ⚠️ 已知：检测函数对本批（2026-09-19）水印漏检（base+14 门槛过高）。
    #    故当检测为空、且原图底部 6% 存在"右侧浅色块"迹象时，保守多裁 90px。
    if not wy0 and not cut_override:
        tail = g[int(h * 0.94):, :]
        right = tail[:, int(tail.shape[1] * 0.55):]
        if right.mean() > 60:   # 底部右侧偏亮 → 疑似水印
            cut_h = min(cut_h, int(h * 0.955))
            print('  ⚠️ 检测未命中但底部偏亮 → 保守裁至 y=%d（建议目检复核）' % cut_h)
    if cut_h < h * 0.9:
        print('  ⚠️ 裁切量偏大（剩余 %.0f%%），请确认主体未被切' % (cut_h / h * 100))
    im = im.crop((0, 0, w, cut_h))

    # ② 统一 3:4（居中裁宽，只裁不放）
    tw = int(round(cut_h * 3 / 4))
    if tw <= w:
        x0 = (w - tw) // 2
        im = im.crop((x0, 0, x0 + tw, cut_h))
        print('  裁至 3:4: %dx%d（横向居中裁掉 %dpx）' % (*im.size, w - tw))
    else:
        im = im.crop((0, 0, w, int(round(w * 4 / 3))))
        print('  裁至 3:4: %dx%d' % im.size)

    # ③ 放大到目标尺寸（受限）
    k = W / im.width
    if k > MAX_UPSCALE:
        raise SystemExit('放大倍数 %.2f 超过上限 %.2f，请重生成' % (k, MAX_UPSCALE))
    im = im.resize((W, H), Image.LANCZOS)
    print('  缩放 %.3fx → %dx%d' % (k, W, H))

    # ④ 保护性暗化（保证浅色字可读）
    im = Image.blend(im, Image.new('RGB', (W, H), veil_c), veil_a)

    # ⑤ 柔化：减高频噪点 → JPEG 更易压进 100KB。底图仅作氛围，文字是后画的，不受影响
    im = im.filter(ImageFilter.GaussianBlur(blur))

    # ⑥ 顶部压字区
    if top_dark > 0:
        im = darken_top(im, strength=top_dark)
        print('  顶部压字区 strength=%.2f' % top_dark)

    # ⑦ 输出底部条带供人工目检（水印以目检为最终判据）
    strip_h = int(H * 0.18)
    im.crop((0, H - strip_h, W, H)).save(
        os.path.join(dst, '_目检底_%s' % out_name), 'JPEG', quality=95)
    print('  目检条带 → _目检底_%s（请确认无水印）' % out_name)

    # ⑧ 保存
    p = os.path.join(dst, out_name)
    im.save(p, 'PNG')
    g2 = np.array(im.convert('L')).astype(float)
    print('  输出 %s  %dx%d  %.1fKB  亮度均值 %.1f'
          % (out_name, W, H, os.path.getsize(p) / 1024, g2.mean()))
    return True


def resolve(base, ref):
    """把文件名/相对名解析为绝对路径（先查 底图/ 目录，否则当绝对路径）"""
    cand = os.path.join(base, '_过程文件', '底图', ref)
    return cand if os.path.exists(cand) else ref


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', required=True, help='卡片文章根目录')
    ap.add_argument('--cover', required=True, help='封面卡底图（文件名或绝对路径）')
    ap.add_argument('--closing', required=True, help='收尾卡底图（文件名或绝对路径）')
    ap.add_argument('--cover-top', type=float, default=0.52, help='封面卡顶部压字强度')
    ap.add_argument('--closing-top', type=float, default=0.30, help='收尾卡顶部压字强度')
    ap.add_argument('--cover-blur', type=float, default=1.1)
    ap.add_argument('--closing-blur', type=float, default=1.1)
    ap.add_argument('--prefix', default='', help='篇号前缀（如 第14篇）——必须给，否则会覆盖别篇成品')
    ap.add_argument('--cut-bottom', type=int, default=0,
                    help='手动指定裁切高度（像素）——目检发现水印残留时用它硬裁，如 1560')
    a = ap.parse_args()

    dst = os.path.join(a.base, '_过程文件', '底图成品')
    os.makedirs(dst, exist_ok=True)

    pre = (a.prefix.strip() + '_') if a.prefix.strip() else ''
    jobs = [
        (resolve(a.base, a.cover), pre + '封面卡_底图.png', 0.20, '#241c14', a.cover_top, a.cover_blur),
        (resolve(a.base, a.closing), pre + '收尾卡_底图.png', 0.14, '#241c14', a.closing_top, a.closing_blur),
    ]
    ok = True
    for src, out, va, vc, td, bl in jobs:
        if not os.path.exists(src):
            print('✗ 缺文件：%s' % src)
            ok = False
            continue
        prep(src, dst, out, va, vc, td, bl, a.cut_bottom)
    print('\n%s' % ('处理完成，请目检底部条带 ✅' if ok else '存在未通过项 ❌'))


if __name__ == '__main__':
    main()
