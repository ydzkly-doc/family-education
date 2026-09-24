# -*- coding: utf-8 -*-
"""
剪映窗口 z-order / 遮挡关系探测（只读，不点击任何东西）

回答三个问题：
  1. 剪映窗口现在在哪、是不是前台窗口
  2. 它上面盖着谁（决定盲点点击会不会误操作别的软件）
  3. 鼠标/键盘注入能力是否可用（只移动光标并读回，不点击）
"""
import sys
import io
import ctypes
from ctypes import wintypes

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

u32 = ctypes.windll.user32

# 显式声明签名，避免 64 位下句柄被截断
u32.EnumWindows.argtypes = [ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM), wintypes.LPARAM]
u32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
u32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
u32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
u32.IsWindowVisible.argtypes = [wintypes.HWND]
u32.WindowFromPoint.argtypes = [wintypes.POINT]
u32.WindowFromPoint.restype = wintypes.HWND
u32.GetAncestor.argtypes = [wintypes.HWND, ctypes.c_uint]
u32.GetAncestor.restype = wintypes.HWND
u32.GetForegroundWindow.restype = wintypes.HWND
u32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
u32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]


def title_of(hwnd):
    buf = ctypes.create_unicode_buffer(512)
    u32.GetWindowTextW(hwnd, buf, 512)
    return buf.value


def class_of(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    u32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def pid_of(hwnd):
    pid = wintypes.DWORD()
    u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


# Z 序从上到下枚举可见顶层窗口
zorder = []


@ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
def cb(hwnd, lparam):
    if u32.IsWindowVisible(hwnd):
        t = title_of(hwnd)
        r = wintypes.RECT()
        u32.GetWindowRect(hwnd, ctypes.byref(r))
        if t and r.right - r.left > 100:
            zorder.append({
                "hwnd": hwnd, "title": t, "cls": class_of(hwnd),
                "pid": pid_of(hwnd),
                "rect": (r.left, r.top, r.right, r.bottom),
            })
    return True


u32.EnumWindows(cb, 0)

print("=" * 66)
print("① Z 序清单（越靠前 = 越在顶层）")
print("=" * 66)
for i, w in enumerate(zorder[:18]):
    mark = "  <== 剪映" if "剪映" in w["title"] else ""
    l, t, r, b = w["rect"]
    print(f"{i:>3}. {w['title'][:34]:<36} pid={w['pid']:<7} [{l},{t} {r-l}x{b-t}]{mark}")

# 定位剪映
jy = next((w for w in zorder if "剪映" in w["title"]), None)
fg = u32.GetForegroundWindow()

print()
print("=" * 66)
print("② 前台窗口判定")
print("=" * 66)
print(f"  当前前台窗口：{title_of(fg)!r}  (pid={pid_of(fg)})")
print(f"  剪映是否前台：{'是 ✅' if jy and jy['hwnd'] == fg else '否 ❌ —— 剪映被盖住了'}")

if jy:
    l, t, r, b = jy["rect"]
    print(f"  剪映窗口矩形：({l}, {t}) - ({r}, {b})")

    print()
    print("=" * 66)
    print("③ 剪映窗口范围内，实际在最上层的是谁？")
    print("=" * 66)
    pts = [
        ("左上区", l + (r - l) // 5, t + (b - t) // 5),
        ("正中区", l + (r - l) // 2, t + (b - t) // 2),
        ("右下区", l + (r - l) * 4 // 5, t + (b - t) * 4 // 5),
    ]
    hijack = 0
    for label, px, py in pts:
        h = u32.WindowFromPoint(wintypes.POINT(px, py))
        top = u32.GetAncestor(h, 2) or h  # GA_ROOT
        tt = title_of(top) or title_of(h)
        is_jy = "剪映" in tt
        if not is_jy:
            hijack += 1
        print(f"  {label} ({px},{py}) -> {tt[:40]!r} {'[剪映]' if is_jy else '[被遮挡!]'}")
    print(f"\n  >> 3 个采样点中被遮挡 {hijack} 个")

# ---- 鼠标注入能力测试：只移动光标并读回，绝不点击 ----
print()
print("=" * 66)
print("④ 光标控制能力（仅移动，不点击）")
print("=" * 66)
orig = wintypes.POINT()
u32.GetCursorPos(ctypes.byref(orig))
print(f"  当前光标位置：({orig.x}, {orig.y})")

if jy:
    tx, ty = l + (r - l) // 2, t + (b - t) // 2
    moved = u32.SetCursorPos(tx, ty)
    got = wintypes.POINT()
    u32.GetCursorPos(ctypes.byref(got))
    print(f"  SetCursorPos 返回值：{moved}")
    print(f"  目标坐标：({tx}, {ty})   实际落点：({got.x}, {got.y})")
    print(f"  >> 光标注入：{'可用 ✅' if (got.x, got.y) == (tx, ty) else '不可用 ❌'}")
    # 复位到原点，不留痕迹
    u32.SetCursorPos(orig.x, orig.y)
    back = wintypes.POINT()
    u32.GetCursorPos(ctypes.byref(back))
    print(f"  已复位到 ({back.x}, {back.y})")

print()
print("[探测完成 —— 全程未发生任何点击]")
