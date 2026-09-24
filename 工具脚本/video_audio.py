# -*- coding: utf-8 -*-
r"""
音频处理链 —— 口播声音美化（降噪 / 去齿音 / 音色塑形 / 响度标准化）

对应剪映的「声音美化」，但每一步都**参数可量化、可复现**。

处理链顺序（顺序很重要，别随意调换）：
  ① highpass       去低频隆隆声（空调、桌面震动、手持噪声）
  ② arnndn         神经网络降噪（RNNoise，需 .rnnn 模型）
  ③ afftdn         传统 FFT 降噪（可与 arnndn 叠加或单独用）
  ④ deesser        去齿音（"嘶/次"的刺耳感）
  ⑤ equalizer      多段 EQ —— 这一步决定"音色"的冷/暖/厚/薄
  ⑥ acompressor    压缩，让音量更稳、声音更"实"
  ⑦ loudnorm       响度标准化（放最后，两遍法，线性更精确）

为什么 loudnorm 必须放最后：它按整段统计响度，前面任何处理都会改变响度，
放前面会导致最终响度不达标。

⚠️ Windows 路径坑：滤镜参数用 ':' 分隔，`model=C:\x\rnnn` 会被吃坏。
   → 处理方式是**把 cwd 切到模型所在目录、只传文件名**（与视频侧同一套办法）。

用法：
  python video_audio.py --analyze <文件>                    # 只测响度，不改文件
  python video_audio.py --presets                           # 列出预设
  python video_audio.py --process <入> <出> --preset 标准     # 套预设处理
  python video_audio.py --ab <文件> --outdir <目录>          # 生成多档对比，供调参
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

FFMPEG = r"C:\Users\ZhuanZ\.workbuddy\binaries\ffmpeg\bin\ffmpeg.exe"
RNNN_DIR = r"C:\Users\ZhuanZ\.workbuddy\binaries\ffmpeg\models\arnndn"


# ============================ 参数定义 ============================
# 每一项都可单独调；enabled=False 即跳过该环节
DEFAULT = {
    "highpass": {"enabled": True, "f": 80},              # Hz，男声 70~90，女声 90~120
    "arnndn":   {"enabled": True, "model": "bd.rnnn", "mix": 0.8},
    #           mix: 0~1，越大降噪越狠但可能伤音质。0.8 是常用平衡点，0.95 激进
    "afftdn":   {"enabled": False, "nf": -25},
    #           nf: 噪声底（dB）。-25 中等 / -20 激进 / -40 温和
    "deesser":  {"enabled": True, "i": 0.4, "m": 0.5, "f": 0.5},
    #           i: 强度 0~1；m: 最大去齿量；f: 中心频率（0~1，越大越靠高频）
    "eq":       [{"f": 180, "w": 1.0, "g": -2.0},        # 减一点闷浑
                 {"f": 400, "w": 1.0, "g": -1.0},        # 减一点"盒子音"
                 {"f": 3000, "w": 1.2, "g": 2.0},        # 提清晰度（咬字）
                 {"f": 8000, "w": 1.5, "g": 1.0}],       # 提一点空气感
    "compressor": {"enabled": True, "threshold": -18, "ratio": 3.0,
                   "attack": 20, "release": 250, "makeup": 1.0},
    "loudnorm": {"enabled": True, "I": -14.0, "TP": -1.5, "LRA": 11.0,
                 "two_pass": True},
    #           I: 目标整合响度(LUFS)。短视频平台常用 -14；越大越响
    #           TP: 真峰值上限(dBTP)。-1.5 留安全余量
    #           LRA: 响度范围，口播 11 左右较自然
    "alimiter": {"enabled": True, "headroom_db": 1.0, "attack": 5, "release": 50,
                 "level": False},
    #           ⚠️ 必须有这一道：实测**单遍 loudnorm 压不住真峰值**
    #           （目标 -1.5 dBTP，实测产出 +0.71 dBTP，已过 0 有削波风险）
    #           level=False 很重要——true 会自动抬电平，把 loudnorm 的成果毁掉
    #           headroom_db: alimiter 限的是**采样峰值**，而 dBTP 是**真峰值**
    #           （含采样间过冲），两者实测差约 0.9 dB。
    #           故限制点 = TP目标 - headroom_db。-1.5 目标配 1.0 余量 → 限在 -2.5 dB，
    #           实测产出 TP = -1.59 dBTP ✅（不这么算就会得到 -0.63，白设）
}

# ⚠️ 链尾必须做一次采样格式归一化，且必须**显式指定采样率**。
# 原因一：arnndn（RNNoise）按 480 样本分帧，其输出帧长与本构建的 AAC 编码器不兼容，
#        会报 "Error submitting audio frame to the encoder: Invalid argument"。
#        实测：输出 float(fltp) → 失败；输出 s16 → 成功。
#        放在链尾（而非紧跟 arnndn）可保住中间环节的浮点精度。
# 原因二：不写 sample_rates 的话，采样率会被 arnndn 顶到 96000 Hz，
#        体积白白翻倍且部分平台兼容性差。故显式钉死 48000（视频行业标准）。
OUT_FORMAT = "aformat=sample_fmts=s16:sample_rates=48000:channel_layouts=stereo"

# 预设：直接改参数，不用背滤镜语法
PRESETS = {
    "关闭": {},
    "轻": {"arnndn": {"enabled": True, "mix": 0.6},
           "deesser": {"enabled": True, "i": 0.25},
           "eq": [], "compressor": {"enabled": False},
           "loudnorm": {"I": -16.0}},
    "标准": {},                                   # = DEFAULT
    "强": {"arnndn": {"enabled": True, "mix": 0.95},
           "afftdn": {"enabled": True, "nf": -20},
           "deesser": {"enabled": True, "i": 0.6},
           "compressor": {"threshold": -20, "ratio": 4.0}},
    "仿剪映声音美化": {"arnndn": {"enabled": True, "mix": 0.85},
                       "deesser": {"enabled": True, "i": 0.5, "f": 0.6},
                       "eq": [{"f": 200, "w": 1.0, "g": -3.0},
                              {"f": 3500, "w": 1.0, "g": 2.5},
                              {"f": 10000, "w": 1.5, "g": 1.5}],
                       "compressor": {"enabled": True, "threshold": -20,
                                      "ratio": 3.5, "makeup": 1.5},
                       "loudnorm": {"I": -14.0, "TP": -1.0}},
}


def merge(base: dict, override: dict) -> dict:
    """浅合并：override 里出现的键整体替换（含 dict），方便"整块换掉某环节" """
    out = {k: (dict(v) if isinstance(v, dict) else list(v) if isinstance(v, list) else v)
           for k, v in base.items()}
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k].update(v)
        else:
            out[k] = v
    return out


def resolve(preset: str) -> dict:
    return merge(DEFAULT, PRESETS.get(preset, {}))


# ============================ 滤镜串编译 ============================
def build_chain(cfg: dict, need_model_dir: bool = True) -> tuple[str, str | None]:
    """
    返回 (滤镜串, 需要切换到的 cwd)。
    cwd 不为 None 时，调用方必须用该目录作为 subprocess 的 cwd，
    否则 arnndn 的 model 路径会因 Windows 盘符冒号解析失败。
    """
    parts, cwd = [], None

    hp = cfg.get("highpass", {})
    if hp.get("enabled"):
        parts.append(f"highpass=f={hp.get('f', 80)}")

    ar = cfg.get("arnndn", {})
    if ar.get("enabled"):
        model = ar.get("model", "bd.rnnn")
        mix = ar.get("mix", 0.8)
        parts.append(f"arnndn=model={os.path.basename(model)}:mix={mix}")
        cwd = RNNN_DIR if need_model_dir else None

    af = cfg.get("afftdn", {})
    if af.get("enabled"):
        parts.append(f"afftdn=nf={af.get('nf', -25)}")

    ds = cfg.get("deesser", {})
    if ds.get("enabled"):
        parts.append(f"deesser=i={ds.get('i', 0.4)}:m={ds.get('m', 0.5)}:f={ds.get('f', 0.5)}")

    for band in cfg.get("eq", []) or []:
        parts.append(f"equalizer=f={band['f']}:width_type=o:width={band.get('w', 1.0)}:g={band['g']}")

    cp = cfg.get("compressor", {})
    if cp.get("enabled"):
        # acompressor 用线性阈值，需把 dB 换算成线性：10^(dB/20)
        thr_db = cp.get("threshold", -18)
        thr_lin = round(10 ** (thr_db / 20), 6)
        parts.append(
            f"acompressor=threshold={thr_lin}:ratio={cp.get('ratio', 3.0)}"
            f":attack={cp.get('attack', 20)}:release={cp.get('release', 250)}"
            f":makeup={cp.get('makeup', 1.0)}"
        )

    return ",".join(parts), cwd


def build_loudnorm(cfg: dict, measured: dict | None = None) -> str:
    ln = cfg.get("loudnorm", {})
    if not ln.get("enabled"):
        return ""
    base = f"I={ln.get('I', -14.0)}:TP={ln.get('TP', -1.5)}:LRA={ln.get('LRA', 11.0)}"
    if measured and ln.get("two_pass", True):
        m = measured
        return (f"loudnorm={base}"
                f":measured_I={m['input_i']}:measured_TP={m['input_tp']}"
                f":measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}"
                f":offset={m['target_offset']}:linear=true:print_format=summary")
    return f"loudnorm={base}"


def build_post(cfg: dict) -> str:
    """loudnorm 之后的两道：真峰值限制 + 采样格式归一化（顺序不可换）"""
    parts = []
    al = cfg.get("alimiter", {})
    if al.get("enabled"):
        # 限制点 = 真峰值目标 - 余量（见 DEFAULT 里的说明）
        tp_target = cfg.get("loudnorm", {}).get("TP", -1.5)
        limit_db = tp_target - al.get("headroom_db", 1.0)
        lim = round(10 ** (limit_db / 20), 6)
        parts.append(f"alimiter=limit={lim}:level={1 if al.get('level') else 0}"
                     f":attack={al.get('attack', 5)}:release={al.get('release', 50)}")
    parts.append(OUT_FORMAT)
    return ",".join(parts)


def build_full_chain(cfg: dict, measured: dict | None = None) -> tuple[str, str | None]:
    """组装完整链，返回 (滤镜串, 需要的 cwd)"""
    pre, cwd = build_chain(cfg)
    ln = build_loudnorm(cfg, measured)
    post = build_post(cfg)
    return ",".join(x for x in (pre, ln, post) if x), cwd


# ============================ 执行 ============================
def run(args, cwd=None, label=""):
    if label:
        print(f"    · {label}")
    p = subprocess.run(args, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", cwd=cwd)
    return p


def analyze(src: str, pre_chain: str | None = None, cwd: str | None = None) -> dict | None:
    """
    第一遍：测响度（不改文件）

    ⚠️ 关键：loudnorm 的两遍法要求**在被测信号上测**。
      loudnorm 前面还有降噪/EQ/压缩时，这些环节会改变响度，
      所以在「前置链之前」测会算错补偿量。
      实测踩过：目标 -14 LUFS，成片只到 -15.86（差 1.86 LU）。
      → pre_chain 传进来，测量时一并应用，测到的才是 loudnorm 真正要处理的信号。
    """
    print("  [响度分析]" + ("（含前置链）" if pre_chain else ""))
    af = ",".join(x for x in (pre_chain, "loudnorm=print_format=json") if x)
    p = run([FFMPEG, "-hide_banner", "-i", os.path.abspath(src), "-af", af,
             "-f", "null", "-"], cwd=cwd)
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", p.stderr or "", re.S)
    if not m:
        print("    分析失败，未取到 JSON")
        return None
    try:
        d = json.loads(m.group(0))
    except Exception as e:
        print(f"    解析失败：{e}")
        return None
    print(f"    整合响度 I      = {d.get('input_i')} LUFS   （目标 {DEFAULT['loudnorm']['I']}）")
    print(f"    真峰值   TP     = {d.get('input_tp')} dBTP   （上限 {DEFAULT['loudnorm']['TP']}）")
    print(f"    响度范围 LRA    = {d.get('input_lra')}")
    print(f"    噪声阈值 thresh = {d.get('input_thresh')}")
    print(f"    需增益   offset = {d.get('target_offset')} dB")

    # ---------- 达标可行性预判 ----------
    # 同时满足「响度 I」与「真峰值 ≤ TP」的硬约束是 PLR（峰值-响度比）：
    #   所需 PLR 上限 = TP目标 - I目标
    # 素材 PLR 超过它 → 限制器会把峰值硬压下去，响度随之掉，**无论怎么调 loudnorm 都补不回来**。
    # （实测过 5 种方案全部卡在 TP≈-1.74、响度差 1.7~2.6 LU，根因就在这里）
    try:
        cur_i = float(d["input_i"])
        cur_tp = float(d["input_tp"])
        plr = cur_tp - cur_i
        i_t = DEFAULT["loudnorm"]["I"]
        tp_t = DEFAULT["loudnorm"]["TP"]
        allowed = tp_t - i_t
        print()
        print(f"    PLR（峰值−响度比）= {plr:.2f} dB")
        print(f"    达标所需上限     = {allowed:.2f} dB")
        if plr <= allowed:
            print(f"    → ✅ 素材动态范围适中，可同时达标")
        else:
            gap = plr - allowed
            print(f"    → ⚠️ 超标 {gap:.2f} dB，**无法同时达标**")
            print(f"       预计最终响度只能到约 {i_t - gap:.1f} LUFS（差 {gap:.1f} LU）")
            print("       可选：")
            print("         ① 接受现状（各平台一般会再做一次归一化，影响有限）")
            new_tp = tp_t + gap
            if new_tp <= -0.5:
                print(f"         ② 放宽真峰值上限到 <={new_tp:.1f} dBTP")
            else:
                print(f"         ② 放宽真峰值不可行（需 {new_tp:+.1f} dBTP，已过 0 会削波）")
            print("         ③ 加强压缩以降低 PLR（牺牲部分动态，口播通常可接受）")
    except (KeyError, TypeError, ValueError):
        pass
    return d


def process(src: str, dst: str, cfg: dict, workdir: str | None = None) -> bool:
    pre, cwd = build_chain(cfg)
    # ⚠️ 必须带着前置链测，否则补偿量算错（见 analyze 的说明）
    measured = analyze(src, pre, cwd) if (cfg.get("loudnorm", {}).get("enabled")
                                          and cfg["loudnorm"].get("two_pass", True)) else None
    ln = build_loudnorm(cfg, measured)
    post = build_post(cfg)
    chain = ",".join(x for x in (pre, ln, post) if x)
    if not chain.strip(OUT_FORMAT).strip(","):
        print("  未启用任何环节，直接复制")
        import shutil
        shutil.copy(src, dst)
        return True

    print(f"  [滤镜链]\n    {chain}")
    if cwd:
        print(f"  [cwd] {cwd}（规避 model 路径冒号问题）")

    p = run([FFMPEG, "-hide_banner", "-y", "-i", os.path.abspath(src),
             "-af", chain, "-c:v", "copy",
             "-c:a", "aac", "-b:a", "192k", os.path.abspath(dst)], cwd=cwd)
    if p.returncode != 0:
        print("  !! 失败：")
        for line in (p.stderr or "").splitlines()[-10:]:
            print(f"     {line}")
        return False
    print(f"  ✓ {os.path.basename(dst)}  ({os.path.getsize(dst)/1024/1024:.1f} MB)")
    return True


def ab_test(src: str, outdir: str, presets: list[str] | None = None):
    """对同一素材跑多档预设，便于一起听/看对比"""
    os.makedirs(outdir, exist_ok=True)
    presets = presets or ["关闭", "轻", "标准", "强", "仿剪映声音美化"]
    base = os.path.splitext(os.path.basename(src))[0]
    print("=" * 70)
    print("A/B 对比（对同一段素材套不同参数）")
    print("=" * 70)
    rows = []
    for name in presets:
        cfg = resolve(name)
        dst = os.path.join(outdir, f"{base}__{name}.mp4")
        print(f"\n【{name}】")
        ok = process(src, dst, cfg)
        rows.append((name, dst if ok else None))
    print()
    print("=" * 70)
    print("对比产物")
    print("=" * 70)
    for name, p in rows:
        print(f"  {'✓' if p else '✗'} {name:<16} {p or ''}")
    print("\n建议：逐个打开听，重点听 —— ① 背景噪声还剩多少 ② 齿音刺不刺 "
          "③ 人声是否发闷/过亮 ④ 音量是否平稳")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--analyze")
    ap.add_argument("--process", nargs=2, metavar=("IN", "OUT"))
    ap.add_argument("--ab")
    ap.add_argument("--outdir")
    ap.add_argument("--preset", default="标准")
    ap.add_argument("--presets", action="store_true", help="列出所有预设")
    args = ap.parse_args()

    if args.presets:
        print("可用预设：")
        for name, over in PRESETS.items():
            print(f"  {name:<16} {'（即默认参数）' if not over else over}")
        print("\n默认参数：")
        print(json.dumps(DEFAULT, ensure_ascii=False, indent=1))
        return

    if args.analyze:
        print(f"分析：{args.analyze}")
        analyze(args.analyze)
        return

    if args.ab:
        ab_test(args.ab, args.outdir or os.path.join(os.path.dirname(args.ab), "_音频对比"))
        return

    if args.process:
        src, dst = args.process
        cfg = resolve(args.preset)
        print(f"预设：{args.preset}")
        ok = process(src, dst, cfg)
        sys.exit(0 if ok else 1)

    print(__doc__)


if __name__ == "__main__":
    main()
