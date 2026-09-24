# -*- coding: utf-8 -*-
r"""
路径与能力解析 —— 让本技能可移植，不写死任何本机路径

解析顺序（全部支持环境变量覆盖，方便换机器/换目录）：
  ffmpeg   : $WB_FFMPEG → ~/.workbuddy/binaries/ffmpeg/bin/ffmpeg[.exe] → PATH
  模型      : $WB_VIDEO_MODELS → 技能目录/models → ~/.workbuddy/binaries/ffmpeg/models

⚠️ 会**实际校验 ffmpeg 能力**：很多软件自带的 ffmpeg 是阉割版
   （无 libx264、无 ass/subtitles），拿它烧字幕必然失败。
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

# 技能根目录（scripts/ 的上一级）
SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_MODELS = os.path.join(SKILL_ROOT, "models")

WB_HOME = os.path.expanduser("~/.workbuddy")


# ============================ ffmpeg ============================
def _candidates_ffmpeg() -> list[str]:
    c = []
    env = os.environ.get("WB_FFMPEG")
    if env:
        c.append(env)
    c += [
        os.path.join(WB_HOME, "binaries", "ffmpeg", "bin", "ffmpeg.exe"),
        os.path.join(WB_HOME, "binaries", "ffmpeg", "bin", "ffmpeg"),
        r"C:\ffmpeg\bin\ffmpeg.exe",
        "/usr/local/bin/ffmpeg",
        "/opt/homebrew/bin/ffmpeg",
        "/usr/bin/ffmpeg",
    ]
    which = shutil.which("ffmpeg")
    if which:
        c.append(which)
    return c


def _probe(path: str) -> dict:
    """探测 ffmpeg 能力（失败不抛异常，返回空能力表）"""
    cap = {"ok": False, "libx264": False, "ass": False, "drawtext": False,
           "silencedetect": False, "reason": ""}
    try:
        v = subprocess.run([path, "-hide_banner", "-version"],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=20)
        vs = v.stdout or ""
        if v.returncode != 0:
            cap["reason"] = "无法执行 -version"
            return cap
        cap["libx264"] = "libx264" in vs or "enable-libx264" in vs
        # 编码器里查 libx264 更可靠
        e = subprocess.run([path, "-hide_banner", "-encoders"],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=30)
        cap["libx264"] = "libx264" in (e.stdout or "")
        f = subprocess.run([path, "-hide_banner", "-filters"],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=30)
        fs = f.stdout or ""
        cap["ass"] = " ass " in fs
        cap["drawtext"] = "drawtext" in fs
        cap["silencedetect"] = "silencedetect" in fs
        cap["ok"] = cap["ass"] and cap["silencedetect"]
        if not cap["ok"]:
            miss = [k for k, ok in (("libx264", cap["libx264"]), ("ass", cap["ass"]),
                                    ("silencedetect", cap["silencedetect"])) if not ok]
            cap["reason"] = "缺少：" + "、".join(miss)
        return cap
    except Exception as e:
        cap["reason"] = f"{type(e).__name__}: {e}"
        return cap


_cache: dict[str, tuple[str, dict]] = {}


def find_ffmpeg(verbose: bool = False) -> tuple[str, dict]:
    """
    返回 (ffmpeg 路径, 能力表)。找不到可用 ffmpeg 时抛 RuntimeError。
    优先返回**能力完整**的；若都不完整，返回能力最好的那个并给出警告。
    """
    if "ffmpeg" in _cache:
        if verbose:
            p, cap = _cache["ffmpeg"]
            print(f"[ffmpeg] {p}  (libx264={cap['libx264']} ass={cap['ass']})")
        return _cache["ffmpeg"]

    best = None
    for p in _candidates_ffmpeg():
        if not p or not os.path.isfile(p):
            continue
        cap = _probe(p)
        if verbose:
            flag = "✅ 完整" if cap["ok"] else f"⚠️ {cap['reason']}"
            print(f"[ffmpeg 探测] {p}  {flag}")
        if cap["ok"]:
            _cache["ffmpeg"] = (p, cap)
            return _cache["ffmpeg"]
        if best is None or (cap["libx264"], cap["ass"]) > (best[1]["libx264"], best[1]["ass"]):
            best = (p, cap)

    if best:
        p, cap = best
        print(f"[警告] 未找到能力完整的 ffmpeg，退用 {p}（{cap['reason']}）",
              file=sys.stderr)
        print("       烧字幕需要含 libass 的完整构建；可用环境变量 WB_FFMPEG 指定。",
              file=sys.stderr)
        _cache["ffmpeg"] = best
        return best

    raise RuntimeError(
        "未找到 ffmpeg。请安装含 libx264 + libass 的完整构建，"
        "或用环境变量 WB_FFMPEG 指定其绝对路径。"
    )


def ffmpeg_path() -> str:
    return find_ffmpeg()[0]


# ============================ 模型 ============================
def _model_roots() -> list[str]:
    c = []
    env = os.environ.get("WB_VIDEO_MODELS")
    if env:
        c.append(env)
    c += [
        SKILL_MODELS,
        os.path.join(WB_HOME, "binaries", "ffmpeg", "models"),
    ]
    return c


def find_rnnn_model(name: str = "bd.rnnn") -> str | None:
    """找 RNNoise 降噪模型（.rnnn，ffmpeg 不自带，需另下）"""
    base = os.path.basename(name)
    for root in _model_roots():
        for sub in ("arnndn", ""):
            p = os.path.join(root, sub, base) if sub else os.path.join(root, base)
            if os.path.isfile(p):
                return p
    return None


def resolve_whisper(model: str) -> str:
    """
    把模型名（tiny/base/small/medium/large-v3）解析为本地路径（若有），
    否则原样返回交给 faster-whisper 自行下载。
    """
    if os.path.isdir(model):
        return model
    for root in _model_roots():
        for cand in (f"faster-whisper-{model}", model):
            p = os.path.join(root, cand)
            if os.path.isdir(p) and os.path.isfile(os.path.join(p, "model.bin")):
                return p
    return model


def diagnose() -> int:
    """自检：打印环境解析结果，供 Agent 排查"""
    print("=" * 68)
    print("环境自检")
    print("=" * 68)
    print(f"技能目录 : {SKILL_ROOT}")
    print(f"WB_HOME  : {WB_HOME}")
    print()
    print("[ffmpeg]")
    try:
        p, cap = find_ffmpeg(verbose=True)
        print(f"  选用：{p}")
        print(f"  libx264={cap['libx264']}  ass={cap['ass']}  "
              f"drawtext={cap['drawtext']}  silencedetect={cap['silencedetect']}")
        print(f"  结论：{'✅ 能力完整' if cap['ok'] else '⚠️ ' + cap['reason']}")
    except Exception as e:
        print(f"  ❌ {e}")
    print()
    print("[模型]")
    for root in _model_roots():
        print(f"  搜索目录：{root}  {'存在' if os.path.isdir(root) else '不存在'}")
        if os.path.isdir(root):
            for sub in sorted(os.listdir(root)):
                p = os.path.join(root, sub)
                if os.path.isdir(p):
                    ok = os.path.isfile(os.path.join(p, "model.bin"))
                    print(f"      {sub}/  {'✅ 可用' if ok else ''}")
                elif sub.endswith(".rnnn"):
                    print(f"      {sub}  ✅")
    r = find_rnnn_model()
    print(f"  RNNoise 默认模型：{r or '（未找到，降噪将不可用）'}")
    for m in ("tiny", "small", "medium"):
        print(f"  whisper {m:<8} -> {resolve_whisper(m)}")
    return 0


if __name__ == "__main__":
    sys.exit(diagnose())
