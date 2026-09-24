# -*- coding: utf-8 -*-
"""
剪映窗口内容直抓（PrintWindow）+ 键盘注入能力测试

与 ImageGrab 的区别：PrintWindow 抓的是「窗口自己的内容」，
不受其他窗口遮挡影响 —— 不会再误拍到微信等其它软件。

键盘测试只按一下 Shift（单独按 Shift 对任何软件都无副作用），
并通过 GetAsyncKeyState 读回按下状态来验证注入是否真的生效。
"""
import sys
import io
import os
import ctypes
from ctypes import wintypes

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from PIL import Image

u32 = ctypes.windll.user32
g32 = ctypes.windll.gdi32

u32.EnumWindows.argtypes = [ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM), wintypes.LPARAM]
u32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
u32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
u32.IsWindowVisible.argtypes = [wintypes.HWND]
u32.GetWindowDC.argtypes = [wintypes.HWND]
u32.GetWindowDC.restype = wintypes.HDC
u32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
u32.PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, wintypes.UINT]
u32.PrintWindow.restype = wintypes.BOOL
u32.GetAsyncKeyState.argtypes = [ctypes.c_int]
u32.GetAsyncKeyState.restype = ctypes.c_short
g32.CreateCompatibleDC.argtypes = [wintypes.HDC]
g32.CreateCompatibleDC.restype = wintypes.HDC
g32.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
g32.CreateCompatibleBitmap.restype = wintypes.HBITMAP
g32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
g32.SelectObject.restype = wintypes.HGDIOBJ
g32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
g32.DeleteDC.argtypes = [wintypes.HDC]
# 关键：GetDIBits 的位图句柄是 64 位，必须显式声明，否则 ctypes 按 32 位 int 处理会溢出
g32.GetDIBits.argtypes = [
    wintypes.HDC, wintypes.HBITMAP, wintypes.UINT, wintypes.UINT,
    ctypes.c_void_p, ctypes.c_void_p, wintypes.UINT,
]
g32.GetDIBits.restype = ctypes.c_int


def find_windows(sub):
    out = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, lparam):
        if u32.IsWindowVisible(hwnd):
            buf = ctypes.create_unicode_buffer(512)
            u32.GetWindowTextW(hwnd, buf, 512)
            if sub in buf.value:
                out.append((hwnd, buf.value))
        return True

    u32.EnumWindows(cb, 0)
    return out


print("=" * 66)
print("① 定位剪映窗口")
print("=" * 66)
wins = find_windows("剪映")
if not wins:
    print("  未找到剪映窗口")
    sys.exit(1)
hwnd, wtitle = wins[0]
r = wintypes.RECT()
u32.GetWindowRect(hwnd, ctypes.byref(r))
W, H = r.right - r.left, r.bottom - r.top
print(f"  标题：{wtitle!r}")
print(f"  句柄：{hwnd}")
print(f"  矩形：({r.left},{r.top}) 尺寸 {W}x{H}")

# ---------- PrintWindow 抓窗口自身内容 ----------
print()
print("=" * 66)
print("② PrintWindow 抓取窗口内容（不受遮挡影响）")
print("=" * 66)


class BMIH(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class BMI(ctypes.Structure):
    _fields_ = [("bmiHeader", BMIH), ("bmiColors", wintypes.DWORD * 3)]


out_path = os.path.join(os.environ.get("TEMP", "."), "jy_window_printwindow.png")
img = None
for flag, label in [(2, "PW_RENDERFULLCONTENT"), (0, "PW_CLIENTONLY=0 普通模式")]:
    hdc = u32.GetWindowDC(hwnd)
    mdc = g32.CreateCompatibleDC(hdc)
    bmp = g32.CreateCompatibleBitmap(hdc, W, H)
    g32.SelectObject(mdc, bmp)
    ok = u32.PrintWindow(hwnd, mdc, flag)

    bi = BMI()
    bi.bmiHeader.biSize = ctypes.sizeof(BMIH)
    bi.bmiHeader.biWidth = W
    bi.bmiHeader.biHeight = -H  # 负值 = 自上而下
    bi.bmiHeader.biPlanes = 1
    bi.bmiHeader.biBitCount = 32
    bi.bmiHeader.biCompression = 0
    buf = ctypes.create_string_buffer(W * H * 4)
    g32.GetDIBits(mdc, bmp, 0, H, buf, ctypes.byref(bi), 0)

    im = Image.frombuffer("RGBA", (W, H), buf, "raw", "BGRA", 0, 1).convert("RGB")
    extrema = im.convert("L").getextrema()
    nonzero = sum(1 for p in im.convert("L").getdata() if p > 8)
    ratio = nonzero / (W * H)

    print(f"  {label}: PrintWindow 返回 {ok}，非黑像素占比 {ratio:.1%}")
    if ratio > 0.02:
        img = im
        print("  >> 抓到有效画面 ✅")

    g32.DeleteObject(bmp)
    g32.DeleteDC(mdc)
    u32.ReleaseDC(hwnd, hdc)
    if img:
        break

if img:
    img.save(out_path)
    print(f"  已保存：{out_path}")
else:
    print("  >> PrintWindow 未取到有效画面（GPU 加速窗口常见），需改前台截图方案")

# ---------- 键盘注入能力测试（只按 Shift，无副作用） ----------
print()
print("=" * 66)
print("③ 键盘注入能力（只按一下左 Shift，对任何软件均无副作用）")
print("=" * 66)
VK_SHIFT = 0x10
KEYEVENTF_KEYUP = 0x0002

u32.keybd_event(VK_SHIFT, 0, 0, 0)  # 按下
down_state = u32.GetAsyncKeyState(VK_SHIFT)
u32.keybd_event(VK_SHIFT, 0, KEYEVENTF_KEYUP, 0)  # 抬起
up_state = u32.GetAsyncKeyState(VK_SHIFT)

print(f"  按下时 GetAsyncKeyState = {down_state}  -> 高位为1表示键确实处于按下态")
print(f"  抬起后 GetAsyncKeyState = {up_state}")
injected = (down_state & 0x8000) != 0
print(f"  >> 键盘注入：{'可用 ✅' if injected else '不可用 ❌'}")

print()
print("[完成] 本次只做了按键注入，未点击任何按钮")
