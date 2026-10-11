# -*- coding: utf-8 -*-
# 通用修复：还原朋友圈文案的逐字竖排 + 修话题标签拆字
import os, re, io, glob, sys

root = r"D:\个人资料\家庭教育\公众号\手机方案\视频号文案_v4"

def restore_quote_block(text):
    """把 '朋友圈转发文案' 标题之后、到 '与公众号侧同口径' 之前的逐字 > 行还原成段落。"""
    anchor = "朋友圈转发文案"
    idx = text.find(anchor)
    if idx < 0:
        return text, False
    end_marker = "与公众号侧同口径"
    j = text.find(end_marker, idx)
    if j < 0:
        return text, False
    block = text[idx:j]
    lines = block.split("\n")
    # 找到引用块起点（第一个以 > 开头的行）
    try:
        qstart = next(i for i, ln in enumerate(lines) if ln.lstrip().startswith(">"))
    except StopIteration:
        return text, False
    quote_lines = lines[qstart:]
    # 仅当是竖排（> 单字 连续）才处理
    stripped = [ln[1:].strip() if ln.lstrip().startswith(">") else None for ln in quote_lines]
    content_cells = [c for c in stripped if c is not None and c != ""]
    is_vertical = len(content_cells) >= 10 and all(len(c) <= 2 for c in content_cells) and \
                  sum(1 for c in content_cells if len(c) == 1) >= len(content_cells) * 0.7
    if not is_vertical:
        return text, False
    # 还原：空 quote 行（> 后无内容）作为段落分隔
    paras = []
    cur = ""
    for ln in quote_lines:
        s = ln.strip()
        if not s.startswith(">"):
            # 非引用行（理论上块内没有），跳过
            continue
        cell = s[1:].strip()
        if cell == "":
            if cur:
                paras.append(cur); cur = ""
        else:
            cur += cell
    if cur:
        paras.append(cur)
    # 过滤掉纯标点空段；合并明显的中文标点误分（直接拼接即可，中文不需空格）
    rebuilt = "\n\n".join("> " + p for p in paras if p)
    new_lines = lines[:qstart] + [rebuilt]
    new_block = "\n".join(new_lines).rstrip("\n") + "\n\n"
    text = text[:idx] + new_block + text[j:]
    return text, True

def fix_tags(text):
    """把 `#` `孩` `子` 这类逐字标签还原。"""
    def repl(m):
        cells = re.findall(r"`([^`]*)`", m.group(0))
        joined = "".join(cells)
        # 拆成 #标签 段（按 # 切）
        parts = joined.split("#")
        tags = ["#" + p for p in parts if p]
        return " ".join("`%s`" % t for t in tags)
    # 匹配连续的多个 `单字`（至少4个反引号段）
    pattern = r"(?:`[^`]{1,2}`\s*){4,}"
    return re.sub(pattern, repl, text)

def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    dirs = sorted([d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d)) and d[:2].isdigit()],
                  key=lambda x: x[:2])
    for d in dirs:
        if only and only not in d:
            continue
        mds = glob.glob(os.path.join(root, d, "视频号文案_*.md"))
        if not mds:
            continue
        p = mds[0]
        t = io.open(p, encoding="utf-8").read()
        before = t
        t, did_q = restore_quote_block(t)
        t2 = fix_tags(t)
        did_t = (t2 != t)
        t = t2
        if t != before:
            io.open(p, "w", encoding="utf-8", newline="").write(t)
        print(f"{d[:2]} 朋友圈={'修复' if did_q else '—'} 标签={'修复' if did_t else '—'}")

main()
