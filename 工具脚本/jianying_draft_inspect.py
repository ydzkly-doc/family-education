# -*- coding: utf-8 -*-
"""
读取剪映草稿内容，判断是否加密、结构如何（只读，绝不修改草稿）

用法：
  python jianying_draft_inspect.py                  # 列出草稿目录下所有草稿，供选择
  python jianying_draft_inspect.py <草稿文件夹名>    # 检查指定草稿

用途：剪映版本升级后重新确认「draft_content.json 是否仍为加密」——
      若某天变为明文，则"路线B（写文件生成工程）"即可复活。
"""
import os
import sys
import io
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DRAFT_ROOT = r"D:\Program Files\JianyingPro Drafts"


u32 = None  # 占位，保持导入整洁


def find_drafts():
    if not os.path.isdir(DRAFT_ROOT):
        print(f"草稿目录不存在：{DRAFT_ROOT}")
        print("（在剪映的 全局设置-草稿位置 中可查询）")
        sys.exit(1)
    return sorted(d for d in os.listdir(DRAFT_ROOT)
                  if os.path.isdir(os.path.join(DRAFT_ROOT, d)) and not d.startswith("."))


if len(sys.argv) > 1:
    ROOT = os.path.join(DRAFT_ROOT, sys.argv[1])
    if not os.path.isdir(ROOT):
        print(f"草稿不存在：{ROOT}")
        sys.exit(1)
else:
    drafts = find_drafts()
    print(f"草稿目录：{DRAFT_ROOT}")
    print(f"可用草稿（{len(drafts)} 个）：")
    for d in drafts:
        print(f"    {d}")
    print("\n请用参数指定要检查的草稿，例如：")
    print(f'    python jianying_draft_inspect.py "{drafts[0] if drafts else "草稿名"}"')
    sys.exit(0)


def show(path, maxlen=3000):
    name = os.path.relpath(path, ROOT)
    try:
        size = os.path.getsize(path)
    except OSError:
        return
    print()
    print("-" * 64)
    print(f"◆ {name}   ({size} B)")
    print("-" * 64)
    if size == 0:
        print("  （空文件）")
        return
    raw = open(path, "rb").read()
    # 是否像 JSON 明文
    head = raw[:1]
    is_json = head in (b"{", b"[")
    print(f"  JSON 明文？{is_json}    前 16 字节：{raw[:16]!r}")
    if is_json:
        try:
            obj = json.loads(raw.decode("utf-8"))
            txt = json.dumps(obj, ensure_ascii=False, indent=1)
            print(txt[:maxlen] + ("\n  ...(已截断)" if len(txt) > maxlen else ""))
        except Exception as e:
            print(f"  解析失败：{e}")
            print(raw[:600].decode("utf-8", "replace"))
    else:
        # 尝试解码看是不是乱码（加密特征）
        txt = raw[:400].decode("utf-8", "replace")
        printable = sum(1 for c in txt if c.isprintable() or c in "\r\n\t")
        print(f"  可打印字符占比：{printable / max(1, len(txt)):.0%}")
        print(f"  内容预览：{txt[:400]!r}")


print("=" * 64)
print("顶层 JSON 文件")
print("=" * 64)
for f in ["draft_content.json", "draft_meta_info.json", "timeline_layout.json",
          "key_value.json", "draft_settings", "draft_agency_config.json"]:
    p = os.path.join(ROOT, f)
    if os.path.exists(p):
        show(p)

print()
print("=" * 64)
print("Timelines / <UUID> 子目录（新式结构，真正的数据可能在这）")
print("=" * 64)
tl = os.path.join(ROOT, "Timelines")
if os.path.isdir(tl):
    for uid in os.listdir(tl):
        d = os.path.join(tl, uid)
        if not os.path.isdir(d):
            continue
        print(f"\n>> {uid}")
        for dirpath, dirnames, filenames in os.walk(d):
            for fn in sorted(filenames):
                p = os.path.join(dirpath, fn)
                rel = os.path.relpath(p, d)
                sz = os.path.getsize(p)
                print(f"   {sz:>9} B  {rel}")
        # 挑最大的 json 细看
        biggest = None
        for dirpath, dirnames, filenames in os.walk(d):
            for fn in filenames:
                p = os.path.join(dirpath, fn)
                if biggest is None or os.path.getsize(p) > os.path.getsize(biggest):
                    biggest = p
        if biggest:
            print(f"\n   —— 最大文件内容预览：{os.path.relpath(biggest, d)}")
            show(biggest, 2500)

print()
print("[只读检查完成，草稿目录未被修改]")
