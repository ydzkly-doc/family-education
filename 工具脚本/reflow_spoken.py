#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
把文案 MD 的「二、口播文案」重排成**一行一完整句**（SOP 3.8 的规范格式）。

为什么需要它（2026-09-30 立）：
  早期稿子会把一句话切成好几行——
      `上一条我说，`／`想给那些`／`孩子还没出问题的家庭`／`说点话。`
  机器会自动合并（**不影响出片**），但**人读口播区会以为"该这么断着念"**，
  而且**行数与句数对不上，改稿时数不清**（06 原稿 136 行其实只有 50 句）。
  → 规范：**每行一个完整句**，行间空一行；`【方括号】`提示行原样保留、位置不动。

用法：
    PY="C:/Users/ZhuanZ/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
    "$PY" 工具脚本/reflow_spoken.py "文案.md"            # 重排并写回
    "$PY" 工具脚本/reflow_spoken.py "文案.md" --dry-run   # 只看会变成什么样

⛔ 安全：**只改换行，一个字都不动**——
   重排前后"去掉空白与提示行"的字符流必须完全一致，**不一致就中止、不写回**。
   （幂等：已经规范的稿子跑一次不会有任何变化。）
"""
import argparse
import io
import os
import re
import sys


def flat(text):
    """去掉空白与【提示行】、剥掉粗体记号 → 用于逐字比对"""
    t = re.sub(r"^【.*?】\s*$", "", text, flags=re.M)
    return re.sub(r"[*>\s]", "", t)


def reflow(body):
    """口播区正文 → 一行一完整句（保留【】提示行的位置）"""
    out, buf = [], ""
    for raw in body.split("\n"):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("【"):
            if buf:
                out.append(buf)
                buf = ""
            out.append(line)
            continue
        buf += line
        if re.search(r"[。？！][\u201d\"]?$", buf):
            out.append(buf)
            buf = ""
    if buf:                       # 末尾没有句末标点的残句（理论上不该有）
        out.append(buf)
    return "\n\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("md", help="文案 MD 路径")
    ap.add_argument("--dry-run", action="store_true", help="只打印结果，不写回")
    a = ap.parse_args()

    path = os.path.abspath(a.md)
    if not os.path.isfile(path):
        raise SystemExit(f"❌ 找不到文件：{path}")

    t = io.open(path, encoding="utf-8").read()
    m = re.search(r"(## 二、口播文案\n)(.*?)(\n---\n)", t, re.S)
    if not m:
        raise SystemExit("❌ 找不到「## 二、口播文案」区块（或它后面没有 --- 分隔）")

    head, body, tail = m.group(1), m.group(2), m.group(3)
    new_body = reflow(body)
    # ⚠️ 行数口径：只数**有内容的行**（空行是排版，不是行数），否则会误报"变多了"
    cur = [x.strip() for x in body.split("\n") if x.strip()]
    new = [x.strip() for x in new_body.split("\n") if x.strip()]
    n_sent = len([x for x in new if not x.startswith("【")])

    if flat(body) != flat(new_body):
        a1, b1 = flat(body), flat(new_body)
        print("❌ 文字流不一致，已中止（不写回）")
        print(f"   原 {len(a1)} 字 ／ 新 {len(b1)} 字")
        for i in range(min(len(a1), len(b1))):
            if a1[i] != b1[i]:
                print(f"   首个差异在第 {i} 字：…{a1[max(0, i - 12):i + 12]}… vs "
                      f"…{b1[max(0, i - 12):i + 12]}…")
                break
        sys.exit(1)

    if cur == new:
        print(f"✅ 已是「一行一完整句」（{n_sent} 句 / {len(new)} 行内容），无需改动")
        return

    print(f"口播区：{len(cur)} 行 → {len(new)} 行（{n_sent} 句）")
    print(f"文字流逐字一致 ✅（{len(flat(new_body))} 字）")

    if a.dry_run:
        print("\n── 重排结果（前 12 行）──")
        for line in new_body.split("\n")[:12]:
            print(f"   {line}")
        print("（--dry-run：未写回）")
        return

    io.open(path, "w", encoding="utf-8").write(
        t[:m.start()] + head + "\n" + new_body + tail + t[m.end():])
    print("✅ 已写回")


if __name__ == "__main__":
    main()
