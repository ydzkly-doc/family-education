# -*- coding: utf-8 -*-
"""
剪映专业版 GUI 可操作性探测（只读模式，不做任何点击/修改）

用途：验证本机 AI 助手能否定位并读取剪映窗口，为后续自动化打底。
用法：python jianying_gui_probe.py            # 只读探测
      python jianying_gui_probe.py --shot     # 额外截取主窗口画面
"""
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import psutil
from pywinauto import Desktop

SHOT = "--shot" in sys.argv


def section(t):
    print()
    print("=" * 62)
    print(t)
    print("=" * 62)


# ---------- ① 进程层 ----------
section("① 进程层：剪映进程清单")
procs = []
for p in psutil.process_iter(["pid", "name", "memory_info"]):
    try:
        if p.info["name"] and "jianying" in p.info["name"].lower():
            procs.append(p)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        continue

if not procs:
    print("未发现剪映进程")
    sys.exit(0)

for p in procs:
    mb = p.info["memory_info"].rss / 1024 / 1024
    print(f"  PID {p.pid:<8} 内存 {mb:>8.1f} MB")

main_pid = max(procs, key=lambda x: x.info["memory_info"].rss).pid
print(f"\n>> 主进程判定：PID {main_pid}（内存占用最大）")

# ---------- ② 窗口层 ----------
section("② 窗口层：枚举顶层窗口")
try:
    wins = Desktop(backend="uia").windows()
except Exception as e:
    print("枚举失败：", e)
    wins = []

print(f"共发现 {len(wins)} 个顶层窗口")
jy_wins = []
for w in wins:
    try:
        title = w.window_text()
        pid = w.process_id()
        rect = w.rectangle()
    except Exception:
        continue
    if pid in [p.pid for p in procs] or "剪映" in title:
        jy_wins.append(w)
        print(f"  [剪映] PID {pid:<8} 标题={title!r}")
        print(f"         类名={w.class_name()!r}")
        print(f"         位置={rect.left},{rect.top} 尺寸={rect.width()}x{rect.height()}")
    else:
        print(f"  [其他] PID {pid:<8} 标题={title!r}")

if not jy_wins:
    print("\n未定位到剪映窗口句柄")
    sys.exit(1)

# ---------- ③ 控件树层 ----------
section("③ 控件树层：UIA 结构探测（深度 4）")
target = jy_wins[0]
print(f"目标窗口：{target.window_text()!r}\n")

count = {"n": 0}


def walk(node, depth=0, max_depth=3):
    if depth > max_depth or count["n"] > 60:
        return
    try:
        children = node.children()
    except Exception:
        return
    for c in children:
        if count["n"] > 60:
            return
        count["n"] += 1
        try:
            ct = c.element_info.control_type
            nm = c.window_text() or c.element_info.name or ""
            nm = nm.replace("\n", " ")[:40]
            auto = c.element_info.automation_id or ""
            print(f"  {'  ' * depth}├─ [{ct}] {nm!r}" + (f" id={auto}" if auto else ""))
        except Exception:
            print(f"  {'  ' * depth}├─ <读取失败>")
            continue
        walk(c, depth + 1, max_depth)


walk(target)
print(f"\n>> 可枚举控件数（截断上限 60）：{count['n']}")

# ---------- ④ 截图验证 ----------
if SHOT:
    section("④ 视觉层：截取主窗口画面")
    try:
        from PIL import ImageGrab
        r = target.rectangle()
        img = ImageGrab.grab(bbox=(r.left, r.top, r.right, r.bottom))
        out = r"D:\个人资料\家庭教育\_档案\报告\_剪映窗口截图.png"
        img.save(out)
        print(f"截图已保存：{out}")
        print(f"图像尺寸：{img.size[0]}x{img.size[1]}")
    except Exception as e:
        print("截图失败：", e)

print("\n[探测完成]")
