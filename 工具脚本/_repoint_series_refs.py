# -*- coding: utf-8 -*-
r"""把「内容系列已收进 `公众号/`」这件事，同步到所有文档引用里。

背景（2026-09-29）
    根目录原先 16 个内容系列平铺，现全部移入 `公众号/`。
    于是所有形如 `<系列>/公众号文章` 的路径都要变成 `公众号/<系列>/公众号文章`。

设计原则
    1. **只改路径形态，不改语义**；不碰内容文件本体（`公众号/`、`_备份/`、`_档案/`）。
    2. **先干跑**（--dry-run 默认）：逐行打出 旧→新，人工核对后再加 --apply 落盘。
    3. **SOP 变更日志不改正文**（那是历史记录）——只在其头部加一句"路径归属说明"。

替换顺序（关键：绝对路径先处理，否则相对规则的前置断言会误判）
    R1  `家庭教育学习系统` -> `学习计划`                （学习系统状态目录改名）
    R2  `D:/个人资料/家庭教育/<系列>/`  -> 中间插 `公众号/`
    R3  `D:\个人资料\家庭教育\<系列>\`  -> 中间插 `公众号\`
    R4  `…/<系列>/`                      -> 中间插 `公众号/`
    R5  裸相对 `<系列>/`（前不是 / 或 \）-> 前缀 `公众号/`
    R6  占位符 `<系列>/`                 -> `公众号/<系列>/`

⛔ 两条血泪教训（第一版干跑抓到的，务必保留）
    ① **R5/R6 必须限定"后面接的是已知路径层"**（公众号文章/视频号文案/…）。
       否则会把 `return "王金海讲书/" + parts[1]` 这种**分组用的键**也当成路径前缀——
       那是语义改动，不是路径改动。
    ② **必须排除本脚本自身**：规则文本里就写着这些模式，否则一跑就自伤
       （第一版 12 处命中全在自己身上）。
    另：所有相对规则的**前置否定断言 `(?<![/\\])` 同时兼任幂等保护**——
    `公众号/<系列>/…` 里的 `<系列>` 前面是 `/`，第二次跑不会被再加一层。
"""
import argparse
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HOME = r"C:/Users/ZhuanZ/.workbuddy"
REPO = r"D:/个人资料/家庭教育"
SELF = os.path.abspath(__file__)

SERIES = [
    "为什么学生不喜欢上学", "儿童情绪管理", "如何应对孩子的叛逆", "如何建立和谐师生关系",
    "孩子不上学了怎么办", "孩子为什么说到做不到", "孩子受欢迎能力培养", "孩子总犯错误怎么办",
    "孩子摆烂怎么办", "手机危机处理", "手机方案", "改善你的亲子关系", "智慧父母实践课",
    "父母做到这点孩子会有惊人改变", "王金海讲书", "青春期30讲",
]

# 只有「系列名 + 这些层」才算路径（防止误改普通词）
PATH_LAYERS = ["公众号文章", "视频号文案", "卡片文章", "_过程文件", "_预览", "_档案", "原始材料"]
LAYER_ALT = "|".join(re.escape(x) for x in PATH_LAYERS)

# 扫描根目录（只扫文档；排除内容本体与历史快照）
TARGET_ROOTS = [
    os.path.join(HOME, "skills"),
    os.path.join(HOME, "plugins", "marketplaces", "my-experts", "plugins"),
    os.path.join(HOME, "plugins", "cache", "my-experts"),
    os.path.join(REPO, "_专家", "Codex技能"),
    os.path.join(REPO, "_资产"),
    os.path.join(REPO, "工具脚本"),
]

EXCLUDE_DIR_NAMES = {"_备份", "_backup", "_档案", "_过程文件", "_预览", "__pycache__",
                     ".git", "node_modules", "公众号", "generated-images"}
EXCLUDE_FILE_NAMES = {
    "SOP变更日志.md",       # 历史记录，正文不改（只在头部加归属说明）
    "08-selfcheck.md",      # ⚠️ 其「根目录允许项」规则被本次改动**推翻**，必须人工重写，
}                           #    机械替换会产出半对半错的句子（实测：只改了王金海、漏了青春期30讲）
EXTS = (".md", ".py", ".json", ".txt", ".yaml", ".yml")

LOG_HEAD_NOTE = ("> ⚠️ **2026-09-29 起**：所有内容系列已移入 `公众号/`。"
                 "本文件**历史条目中的路径按当时写法保留**（如 `青春期30讲/公众号文章`），"
                 "当年成立、今天需自行加 `公众号/` 前缀。\n")


def build_rules():
    # R1 只改**路径形态**，不改「概念名」。⚠️「家庭教育学习系统」在本仓库有两重身份：
    #    ① 学习系统的**名字**（提示词、说明文字里的「初始化我的家庭教育学习系统」）—— 不许改；
    #    ② 状态目录的**旧路径名**（`D:/…/家庭教育学习系统/`）—— 要改成 `学习计划/`。
    #    第一版把两者一起替换，会把提示词改成「初始化我的学习计划」，语义全变。
    rules = [
        ("R1a", re.compile(re.escape("D:/个人资料/家庭教育/家庭教育学习系统")),
         "D:/个人资料/家庭教育/学习计划"),
        ("R1b", re.compile(r"(?m)^家庭教育学习系统/$"), "学习计划/"),   # 初始化目录树的根行
    ]
    for s in SERIES:
        e = re.escape(s)
        rules.append(("R2", re.compile(re.escape("D:/个人资料/家庭教育/") + e + "/"),
                      "D:/个人资料/家庭教育/公众号/" + s + "/"))
        rules.append(("R3", re.compile(re.escape(r"D:\个人资料\家庭教育" + "\\") + e + re.escape("\\")),
                      r"D:\个人资料\家庭教育\公众号" + "\\" + s + "\\"))
        rules.append(("R4", re.compile(re.escape("…/") + e + "/"), "…/公众号/" + s + "/"))
        rules.append(("R5", re.compile(r"(?<![/\\])" + e + r"/(?=(" + LAYER_ALT + r"))"),
                      "公众号/" + s + "/"))
    # 王金海讲书 是多一层书名的容器（王金海讲书/<书名>/公众号文章）。
    # ⛔ 必须要求"再下一段才是路径层"，否则会误伤 `return "王金海讲书/" + parts[1]`
    #    这类**分组用的键**（那不是路径）。
    rules.append(("R5b",
                  re.compile(r"(?<![/\\])王金海讲书/([^/\\\s`'\"|)]+)/(?=(" + LAYER_ALT + r"))"),
                  r"公众号/王金海讲书/\1/"))
    rules.append(("R6", re.compile(r"(?<![/\\])<系列>/(?=(" + LAYER_ALT + r"))"), "公众号/<系列>/"))
    return rules


def iter_files():
    for root in TARGET_ROOTS:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIR_NAMES]
            for fn in filenames:
                if not fn.lower().endswith(EXTS):
                    continue
                if fn in EXCLUDE_FILE_NAMES:
                    continue
                full = os.path.join(dirpath, fn)
                if os.path.abspath(full) == SELF:      # ⛔ 排除自身，否则自伤
                    continue
                yield full


def transform(text, rules):
    hits = []
    for tag, rx, repl in rules:
        def _sub(m, tag=tag, repl=repl):
            hits.append((tag, m.group(0), repl))
            return repl
        text = rx.sub(_sub, text)
    return text, hits


def main():
    ap = argparse.ArgumentParser(description="把系列移入公众号/ 的路径变更同步到所有文档")
    ap.add_argument("--apply", action="store_true", help="真正写盘（默认只干跑）")
    ap.add_argument("--quiet", action="store_true", help="干跑时只打汇总")
    args = ap.parse_args()

    rules = build_rules()
    total_files = changed_files = total_hits = 0
    per_tag = {}

    print("=" * 72)
    print("文档引用同步：内容系列 -> 公众号/" + ("（APPLY 落盘）" if args.apply else "（DRY-RUN 只读）"))
    print("=" * 72)

    for path in iter_files():
        total_files += 1
        try:
            with open(path, encoding="utf-8") as f:
                raw = f.read()
        except (UnicodeDecodeError, OSError):
            continue
        new, hits = transform(raw, rules)
        if not hits:
            continue
        changed_files += 1
        total_hits += len(hits)
        for tag, _, _ in hits:
            per_tag[tag] = per_tag.get(tag, 0) + 1
        rel = os.path.relpath(path, REPO) if path.startswith(REPO) else path
        print(f"\n▌{rel}   （{len(hits)} 处）")
        if not args.quiet:
            for i, (old, newl) in enumerate(zip(raw.splitlines(), new.splitlines()), 1):
                if old != newl:
                    print(f"   L{i}  - {old.strip()[:150]}")
                    print(f"        + {newl.strip()[:150]}")
        if args.apply:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new)

    print("\n" + "=" * 72)
    print(f"扫描 {total_files} 个文件；命中 {changed_files} 个；共 {total_hits} 处")
    for tag in sorted(per_tag):
        print(f"   {tag}: {per_tag[tag]}")
    if not args.apply:
        print("\n（干跑结束，未写盘。核对无误后加 --apply）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
