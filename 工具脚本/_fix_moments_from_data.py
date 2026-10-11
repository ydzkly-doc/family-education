# -*- coding: utf-8 -*-
# 用 _v4data_NN.py 里的 moments/tags 重写 md 的「话题标签」行与「朋友圈转发文案」引用块。
# 只动发布方案这两小块，不碰口播/提词器/上屏/合成。
import os, re, io, glob, importlib.util, sys

ROOT = r"D:\个人资料\家庭教育"
V4 = os.path.join(ROOT, "公众号", "手机方案", "视频号文案_v4")
DATA = os.path.join(ROOT, "工具脚本")

def load_item(nn):
    path = os.path.join(DATA, f"_v4data_{nn}.py")
    spec = importlib.util.spec_from_file_location(f"d{nn}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.ITEMS[0]

def build_moments(it):
    m = it["moments"]
    if isinstance(m, str):
        rows = m.split("\n")
    else:
        rows = list(m)
    out = []
    for r in rows:
        out.append(">" if r.strip() == "" else f"> {r}")
    return "\n".join(out)

def build_tags(it):
    t = it["tags"]
    if isinstance(t, str):
        t = t.split()
    return "**话题标签**：" + " ".join(f"`{x}`" for x in t)

def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    files = sorted(glob.glob(os.path.join(V4, "*", "视频号文案_*.md")),
                   key=lambda p: os.path.basename(os.path.dirname(p))[:2])
    n_fixed = 0
    for p in files:
        nn = os.path.basename(os.path.dirname(p))[:2]
        if nn in ("00", "01", "09"):
            continue  # 手工条，单独处理
        if only and only != nn:
            continue
        data_p = os.path.join(DATA, f"_v4data_{nn}.py")
        if not os.path.exists(data_p):
            print(nn, "无数据文件，跳过"); continue
        it = load_item(nn)
        t = io.open(p, encoding="utf-8").read()
        orig = t

        # 1) 标签行（兼容竖排/正常）
        new_tags = build_tags(it)
        t = re.sub(r"^\*\*话题标签\*\*[：:].*$", new_tags, t, count=1, flags=re.M)

        # 2) 朋友圈引用块：按行区间重写。定位标题行与“与公众号侧同口径”行，
        #    把两者之间所有行替换为数据文件重建的引用块（竖排块中间常夹空行，不能靠连续正则）。
        new_quote = build_moments(it)
        lines = t.split("\n")
        i_title = next((i for i, ln in enumerate(lines)
                        if ln.startswith("**⭐ 朋友圈转发文案")), None)
        i_end = next((i for i, ln in enumerate(lines)
                      if "与公众号侧同口径" in ln), None)
        if i_title is not None and i_end is not None and i_end > i_title:
            head = lines[:i_title + 1] + [""] + new_quote.split("\n") + [""]
            tail = lines[i_end:]
            t = "\n".join(head + tail)
        else:
            print(nn, "⚠️ 未定位到朋友圈区间")

        if t != orig:
            io.open(p, "w", encoding="utf-8", newline="").write(t)
            n_fixed += 1
            print(nn, "已修复")
    print("合计修复", n_fixed, "条")

main()
