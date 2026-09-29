# -*- coding: utf-8 -*-
"""孩子不上学了怎么办 系列：高饱和橙 -> 莫兰迪赤陶棕 系统换色。
只替换颜色 hex，不动结构/文字。正文黑灰、米白、浅底中性色保留。"""
import os, re, sys

ROOT = r"D:\个人资料\家庭教育\孩子不上学了怎么办\公众号文章"
PACKS = [
    "发布包_第1篇_接错话",
    "发布包_第2篇_起跑线焦虑",
    "发布包_第3篇_四类高风险家庭",
    "发布包_第4篇_厌学四阶段与九种错误回应",
    "发布包_第5篇_化情大法与湿柴火模型",
    "发布包_第6篇_30秒速览",
]

# 旧色(小写) -> 新色。按角色映射：
# 主色橙系 -> 莫兰迪赤陶棕；强调/正向绿 -> 苔绿；浅橙底 -> 暖陶浅底；
# 台词/方法卡橙 -> 暖琥珀系；中性灰米白保留。
COLOR_MAP = {
    # —— 主色（标题块/竖条/加粗强调/按钮）——
    "#c8612a": "#b06a48",   # 主橙 -> 赤陶棕主色
    "#dd7d34": "#b06a48",   # 次橙 -> 主色
    "#e89a5b": "#c08a5e",   # 亮橙条/边 -> 柔陶棕(辅)
    "#f0b583": "#c08a5e",   # 浅亮橙 -> 柔陶棕
    # —— 深色阶段/深棕文字 ——
    "#b04f20": "#93553a",   # 深橙红(阶段四边) -> 深赤陶
    "#9c4318": "#8a4f33",   # 更深橙红(阶段四标题) -> 深赤陶文字
    "#6b3a17": "#7a4a2e",   # 暗棕标题 -> 深陶棕
    "#8a4b24": "#8a5a3a",   # 棕红小字 -> 陶棕
    # —— 浅橙底 / 卡片底 ——
    "#fef3ea": "#faf3ec",   # 主浅橙底 -> 暖陶白
    "#fff3ea": "#faf3ec",
    "#fdeee2": "#f6ece2",   # 浅橙底2 -> 暖陶浅
    "#f7e0d2": "#f0e2d4",   # 更深浅橙(阶段卡) -> 陶浅
    "#fbe4d2": "#f0e2d4",
    "#f3ddc9": "#ecd9c6",   # 卡片浅棕底 -> 陶浅
    "#f6cfae": "#e5c9ac",   # 较深浅橙 -> 陶中浅
    "#fff8f2": "#fdfaf5",   # 极浅暖白 -> 暖白
    # —— 标题块上的浅色文字 ——
    "#ffe9d9": "#f3e2d4",   # 标题块副文字 -> 浅陶
    "#ffe3cf": "#ecd3c0",   # 标题块更浅文字 -> 浅陶
    # —— 中性 ——
    "#f4f1ec": "#f5f3ef",   # 页脚/背景暖灰 -> 统一暖灰
    "#d8c9bb": "#d9cdbf",   # 分隔/虚线 -> 暖灰
    # —— 突兀绿（黄金干预/正向对勾）-> 莫兰迪苔绿 ——
    "#2e8b57": "#6b8f6a",
}

def remap(path):
    with open(path, "r", encoding="utf-8") as f:
        txt = f.read()
    orig = txt
    def repl(m):
        return COLOR_MAP.get(m.group(0).lower(), m.group(0))
    txt = re.sub(r"#[0-9a-fA-F]{6}", repl, txt)
    # body 背景统一暖灰（原为 #ffffff）
    txt = re.sub(r'(<body[^>]*background:)#ffffff', r'\1#f5f3ef', txt)
    if txt != orig:
        with open(path, "w", encoding="utf-8") as f:
            f.write(txt)
        return True
    return False

for pack in PACKS:
    pdir = os.path.join(ROOT, pack)
    for fn in os.listdir(pdir):
        if not fn.endswith(".html"):
            continue
        if "备份" in fn:
            continue
        if not fn.startswith("正文_第"):
            continue
        path = os.path.join(pdir, fn)
        changed = remap(path)
        print(("[OK] " if changed else "[--] ") + fn)
print("换色完成")
