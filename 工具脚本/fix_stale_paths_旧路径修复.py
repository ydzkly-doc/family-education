# -*- coding: utf-8 -*-
"""修复「系列移入 公众号/ 之后，脚本与配置里遗留的旧绝对路径」。

背景
    2026-09-29 起，16 个内容系列从项目根移入 公众号/。
    仓库已有 `工具脚本/_repoint_series_refs.py` 处理过一批，但它的扫描范围**刻意排除了
    `公众号/`**（为的是不碰内容本体）——于是 **`公众号/` 下各系列的脚本与配置**里仍残留旧路径，
    重跑那一刻才会炸（找不到目录），平时不报错。

做法
    只匹配 **绝对路径** 形态：`家庭教育<分隔符><系列名>` → 在中间补一层 `公众号`。
    - `<分隔符>` 允许 **1~2 个反斜杠或正斜杠**：同时覆盖 Python 里的单反斜杠
      与 **JSON 里的转义双反斜杠**（配置文件 `第NN篇_卡片配置.json` 属后者）。
    - 系列名取 **白名单**（动态读 `公众号/` 下的实有目录）→ 天然不会误伤
      未移动的路径（`_专家`、`_档案`、`工具脚本`、`测试` 等）。
    - **重复跑安全**：补过之后，「系列名」前面已隔着 `公众号`，不再匹配。

范围
    - 文件类型：`.py`（脚本）+ `.json`（卡片配置）
    - 目录：整个项目根，**但排除**  `_备份` / `_备份_*` / `_归档_*` /
      `.git` / `node_modules` / `.workbuddy` / `__pycache__`
    - 文档（`.md` / `.txt`）不在本轮范围，另有 `check_doc_paths.py` 负责巡检

用法
    python fix_stale_paths_旧路径修复.py --dry-run   # 只报告，不改
    python fix_stale_paths_旧路径修复.py             # 执行
"""
import os
import re
import sys
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
PUB = os.path.join(PROJ, '公众号')

# 白名单：公众号/ 下的实有目录 = 真正移动过的系列
SERIES = sorted(d for d in os.listdir(PUB) if os.path.isdir(os.path.join(PUB, d)))
SERIES_SET = set(SERIES)

# 匹配「家庭教育 + 分隔符(1~2 个 \ 或 /) + 一段」；那一段再用白名单判定是不是系列名。
# ⚠️ 不要求系列名后必跟分隔符——`r"D:\...\家庭教育\手机方案"` 这类**目录串结尾**也要覆盖。
# ⚠️ 分隔符吃 1~2 个，是为了同时命中 JSON 里成对写出的转义反斜杠。
PAT = re.compile(r'(家庭教育)([\\/]{1,2})([^\\/"\'\s]+)')

SKIP_DIR_NAMES = {'_备份', '.git', 'node_modules', '.workbuddy', '__pycache__'}
SKIP_DIR_PREFIX = ('_备份_', '_归档_')
TARGET_EXT = ('.py', '.json')
SELF = os.path.abspath(__file__)


def should_skip(path):
    rel = os.path.relpath(path, PROJ).replace('\\', '/')
    for part in rel.split('/'):
        if part in SKIP_DIR_NAMES or part.startswith(SKIP_DIR_PREFIX):
            return True
    return False


def fix_text(text):
    """→ (新文本, 实际改写处数)"""
    n = 0

    def rep(m):
        nonlocal n
        if m.group(3) not in SERIES_SET:          # 非系列名（公众号 / 工具脚本 / _专家 / 测试）→ 原样
            return m.group(0)
        sep = m.group(2)                          # 沿用原分隔符写法（单反斜杠 / 双反斜杠 / 正斜杠）
        n += 1
        return m.group(1) + sep + '公众号' + sep + m.group(3)

    return PAT.sub(rep, text), n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true', help='只报告，不写入')
    args = ap.parse_args()

    print('系列白名单（%d 个）：%s' % (len(SERIES), '、'.join(SERIES)))
    print('文件类型：%s' % '、'.join(TARGET_EXT))
    print('模式：%s' % ('DRY-RUN（不改动）' if args.dry_run else '已写入'))
    print('-' * 80)

    hits = []
    for dirpath, dirnames, filenames in os.walk(PROJ):
        dirnames[:] = [d for d in dirnames if not should_skip(os.path.join(dirpath, d))]
        if should_skip(dirpath):
            continue
        for fn in filenames:
            if not fn.endswith(TARGET_EXT):
                continue
            fp = os.path.join(dirpath, fn)
            if os.path.abspath(fp) == SELF:
                continue
            try:
                with open(fp, encoding='utf-8', newline='') as f:
                    raw = f.read()
            except (UnicodeDecodeError, OSError):
                continue
            new, n = fix_text(raw)
            if new == raw:
                continue
            hits.append((fp, n))
            if not args.dry_run:
                with open(fp, 'w', encoding='utf-8', newline='') as f:
                    f.write(new)

    print('命中 %d 个文件，共 %d 处路径' % (len(hits), sum(n for _, n in hits)))
    print('-' * 80)
    for fp, n in sorted(hits):
        print('  %3d 处  %s' % (n, os.path.relpath(fp, PROJ)))
    if not args.dry_run:
        print('-' * 80)
        print('已改写 %d 个文件' % len(hits))
    return 0


if __name__ == '__main__':
    sys.exit(main())
