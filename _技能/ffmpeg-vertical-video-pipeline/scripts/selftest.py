# -*- coding: utf-8 -*-
r"""
技能自检 —— 不依赖外部素材，用 lavfi 现场合成测试片。

覆盖本次新增的「1~N 段自适应」与「锚点定位」两块：
    ① 锚点定位（anchor / seg / at / start，含未命中处理）
    ② 时间轴换算 map_time（剪停顿后的坐标映射）
    ③ 多段拼接 build_timeline（1/2/5 段、分辨率/帧率混杂、无音轨）
    ④ 过短段合并 merge_short_entries

用法：python selftest.py
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import paths                      # noqa: E402
import video_make as vm           # noqa: E402
import video_visual as vv         # noqa: E402

FFMPEG = paths.ffmpeg_path()
PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(f"  {'✓' if cond else '✗'} {name}" + (f"   {detail}" if detail else ""))


# ---------------- ① 锚点定位 ----------------
def test_anchor():
    print("\n① 锚点定位")
    lines = [
        {"text": "那阵子我儿子老喊肚子疼。", "start": 1.0, "end": 3.2, "matched": True},
        {"text": "检查没查出来，不等于孩子在装。", "start": 3.4, "end": 6.0, "matched": True},
        {"text": "后来我才发现，他是在害怕考试。", "start": 6.2, "end": 9.0, "matched": True},
    ]
    bounds = [(0.0, 9.0), (9.0, 18.0)]

    # 精确包含
    p, err, _ = vm.resolve_place({"anchor": "不等于孩子在装"}, lines, bounds, 3.0)
    check("anchor 精确命中", p is not None and abs(p[0] - 3.4) < 0.01,
          f"{p} err={err}")

    # 忽略标点
    p, err, _ = vm.resolve_place({"anchor": "检查没查出来"}, lines, bounds, 3.0)
    check("anchor 忽略标点", p is not None and abs(p[0] - 3.4) < 0.01, f"{p}")

    # hold 生效
    p, err, _ = vm.resolve_place({"anchor": "不等于孩子在装", "hold": 5.0}, lines, bounds, 3.0)
    check("anchor 的 hold 生效", p is not None and abs((p[1] - p[0]) - 5.0) < 0.01, f"{p}")

    # lead 提前量
    p, err, _ = vm.resolve_place({"anchor": "不等于孩子在装", "lead": 0.4}, lines, bounds, 3.0)
    check("anchor 的 lead 提前量", p is not None and abs(p[0] - 3.0) < 0.01, f"{p}")

    # 模糊命中（错字）
    p, err, _ = vm.resolve_place({"anchor": "不等于孩在装"}, lines, bounds, 3.0)
    check("anchor 容忍错字", p is not None, f"{p} err={err}")

    # 未命中 → 必须返回 None 且带原因
    p, err, _ = vm.resolve_place({"anchor": "完全不存在的句子XYZ"}, lines, bounds, 3.0)
    check("anchor 未命中时返回原因", p is None and bool(err), f"err={err}")

    # 段号
    p, err, _ = vm.resolve_place({"seg": 2}, lines, bounds, 3.0)
    check("seg 段号定位", p is not None and abs(p[0] - 9.0) < 0.01, f"{p}")
    p, err, _ = vm.resolve_place({"seg": 2, "offset": 1.5}, lines, bounds, 3.0)
    check("seg + offset", p is not None and abs(p[0] - 10.5) < 0.01, f"{p}")
    p, err, _ = vm.resolve_place({"seg": 9}, lines, bounds, 3.0)
    check("seg 越界有报错", p is None and bool(err), f"err={err}")

    # 片尾
    p, err, _ = vm.resolve_place({"at": "end", "hold": 4.0}, lines, bounds, 3.0)
    check("at=end 落在片尾前", p is not None and abs(p[0] - 5.0) < 0.01, f"{p}")

    # 显式秒数
    p, err, _ = vm.resolve_place({"start": 2.0, "end": 4.0}, lines, bounds, 3.0)
    check("start/end 显式秒数", p == (2.0, 4.0), f"{p}")

    # 无位置信息
    p, err, _ = vm.resolve_place({"text": "只有文字"}, lines, bounds, 3.0)
    check("无位置信息会报错", p is None and bool(err), f"err={err}")

    # place_cards 支持数组（多张卡）
    cards = vm.place_cards([{"text": "A", "anchor": "肚子疼"},
                            {"text": "B", "anchor": "害怕考试"}], lines, bounds, "金句卡", 3.0)
    check("place_cards 支持多张卡", len(cards) == 2, f"{len(cards)} 张")
    cards = vm.place_cards({"text": "单张", "anchor": "肚子疼"}, lines, bounds, "金句卡", 3.0)
    check("place_cards 支持单对象", len(cards) == 1)

    # ⚠️ 重叠必须自动错开（两条 Dialogue 同时显示会叠字，实测踩过）
    cards = vm.place_cards(
        [{"text": "卡1", "anchor": "肚子疼", "hold": 6.0},
         {"text": "卡2", "anchor": "害怕考试", "hold": 4.0}],
        lines, bounds, "金句卡", 3.0)
    no_overlap = all(cards[i]["end"] <= cards[i + 1]["start"] + 1e-6
                     for i in range(len(cards) - 1))
    check("多卡重叠被自动错开", len(cards) == 2 and no_overlap,
          " ".join(f"[{c['start']},{c['end']}]" for c in cards))

    # 重叠错开后每张仍要有最短可读时长
    check("错开后仍保留最短时长",
          all(c["end"] - c["start"] >= 1.19 for c in cards),
          " ".join(f"{c['end'] - c['start']:.2f}s" for c in cards))

    # 起点超片长要提示（不静默）
    cards = vm.place_cards({"text": "太靠后", "start": 99.0}, lines, bounds,
                           "金句卡", 3.0, total_dur=9.0)
    check("超出片长仍保留但会被提示", len(cards) == 1)


# ---------------- ①b 字幕策略（全程 / 精选 / 无 / 关键词）----------------
def test_subs():
    print("\n①b 字幕策略（subs）")
    lines = [
        {"text": "那阵子我儿子老喊肚子疼。", "start": 1.0, "end": 3.2, "matched": True},
        {"text": "检查没查出来，不等于孩子在装。", "start": 3.4, "end": 6.0, "matched": True},
        {"text": "后来我才发现，他是在害怕考试。", "start": 6.2, "end": 9.0, "matched": True},
    ]
    bounds = [(0.0, 9.0)]

    # 省略 → 全程
    subs = vm.build_subs({}, lines, bounds, 9.0)
    check("默认=全程字幕", len(subs) == 3, f"{len(subs)} 行")

    # all → 全程
    subs = vm.build_subs({"subs": "all"}, lines, bounds, 9.0)
    check('"all" = 全程字幕', len(subs) == 3)

    # none → 无
    subs = vm.build_subs({"subs": "none"}, lines, bounds, 9.0)
    check('"none" = 无字幕', subs == [])

    # 数组 → 精选（只写锚点，文本自动照抄原句）
    subs = vm.build_subs({"subs": [{"anchor": "不等于孩子在装"},
                                   {"anchor": "害怕考试"}]}, lines, bounds, 9.0)
    check("精选字幕只上指定几句", len(subs) == 2, f"{len(subs)} 行")
    check("精选字幕自动照抄原句", subs and subs[0]["text"] == lines[1]["text"],
          f"{subs[0]['text'] if subs else '—'}")
    check("精选字幕时长跟随原句",
          subs and abs(subs[0]["end"] - lines[1]["end"]) < 1e-6,
          f"[{subs[0]['start']},{subs[0]['end']}] vs 原句 [{lines[1]['start']},{lines[1]['end']}]")

    # 精选字幕：可改写上屏文字
    subs = vm.build_subs({"subs": [{"anchor": "他是在害怕考试",
                                    "text": "他是在害怕"}]}, lines, bounds, 9.0)
    check("精选字幕可改写文本", subs and subs[0]["text"] == "他是在害怕",
          f"{subs[0]['text'] if subs else '—'}")

    # 精选字幕：太短的原句要被补到可读时长
    short = [{"text": "嗯。", "start": 2.0, "end": 2.2, "matched": True}]
    subs = vm.build_subs({"subs": [{"anchor": "嗯"}]}, short, [(0, 3)], 3.0)
    check("过短原句会被补足到最短可读时长",
          subs and (subs[0]["end"] - subs[0]["start"]) >= vm.MIN_SUB_HOLD,
          f"{subs[0]['end'] - subs[0]['start']:.2f}s" if subs else "—")

    # 关键词筛选
    subs = vm.build_subs({"subs": {"keep": ["害怕"]}}, lines, bounds, 9.0)
    check("关键词筛选命中 1 行", len(subs) == 1 and "害怕" in subs[0]["text"],
          f"{len(subs)} 行")

    # 关键词筛选：多个词
    subs = vm.build_subs({"subs": {"keep": ["肚子疼", "害怕"]}}, lines, bounds, 9.0)
    check("关键词筛选支持多词", len(subs) == 2, f"{len(subs)} 行")

    # 锚点写错要报错且不静默
    subs = vm.build_subs({"subs": [{"anchor": "根本不存在的句子QQQ"}]}, lines, bounds, 9.0)
    check("精选字幕锚点写错 → 返回空但已提示", subs == [])

    # 不给 text 也不给锚点 → 报错
    subs = vm.build_subs({"subs": [{"hold": 2.0}]}, lines, bounds, 9.0)
    check("缺文本又缺锚点 → 被拒", subs == [])


# ---------------- ② 时间轴换算 ----------------
def test_map_time():
    print("\n② 时间轴换算（剪停顿后坐标映射）")
    keep = [(0.0, 5.0), (7.0, 12.0), (14.0, 20.0)]     # 剪掉了 [5,7) 和 [12,14)
    check("区间内时间不变", vm.map_time(3.0, keep) == 3.0, f"{vm.map_time(3.0, keep)}")
    check("跨过第一个空洞", abs(vm.map_time(7.0, keep) - 5.0) < 1e-6,
          f"{vm.map_time(7.0, keep)}")
    check("跨过两个空洞", abs(vm.map_time(15.0, keep) - 11.0) < 1e-6,
          f"{vm.map_time(15.0, keep)}")
    check("超出末尾返回总长", abs(vm.map_time(999.0, keep) - 16.0) < 1e-6,
          f"{vm.map_time(999.0, keep)}")


# ---------------- ③ 分段合并 ----------------
def test_merge():
    print("\n③ 过短段合并")
    e = [{"file": "a.mp4", "start": 0, "end": 5},
         {"file": "a.mp4", "start": 5, "end": 5.05},     # 过短，应并入前一段
         {"file": "b.mp4", "start": 0, "end": 4}]
    out, merged = vv.merge_short_entries(e)
    check("过短段被合并", merged == 1 and len(out) == 2, f"merged={merged} n={len(out)}")
    check("合并后前段延长", abs(out[0]["end"] - 5.05) < 1e-6, f"{out[0]}")

    e2 = [{"file": "a.mp4", "start": 0, "end": 1}]
    out, merged = vv.merge_short_entries(e2)
    check("单段不合并", merged == 0 and len(out) == 1)


# ---------------- ④ 多段拼接（真跑 ffmpeg） ----------------
def make_clip(path, w, h, fps, dur, color, with_audio=True, tone=440, noise=True):
    """用 lavfi 造一个测试片段；noise=True 时加轻噪声，避免纯色被压成极小文件"""
    src = f"testsrc2=size={w}x{h}:rate={fps}:duration={dur}"
    vf = f"drawbox=x=0:y=0:w=iw:h=ih:color={color}@0.35:t=fill"
    # ⚠️ 所有 -i 必须在所有输出选项之前，否则 -vf 会被当成第二个输入的选项
    args = [FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", src]
    if with_audio:
        args += ["-f", "lavfi", "-i", f"sine=frequency={tone}:duration={dur}"]
    args += ["-vf", vf,
             "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p"]
    if with_audio:
        args += ["-c:a", "aac", "-b:a", "96k", "-shortest"]
    args += [path]
    p = subprocess.run(args, capture_output=True)
    if p.returncode != 0 or not os.path.exists(path):
        print(f"     !! 造片段失败：{os.path.basename(path)}")
        print("        " + (p.stderr or b"").decode("utf-8", "replace")[-700:].replace("\n", "\n        "))


def test_timeline(tmp):
    print("\n④ 多段拼接（真跑 ffmpeg）")
    a = os.path.join(tmp, "s1_320x240_30fps.mp4")
    b = os.path.join(tmp, "s2_480x270_25fps.mp4")      # 不同分辨率 + 不同帧率
    c = os.path.join(tmp, "s3_640x360_30fps.mp4")
    d = os.path.join(tmp, "s4_noaudio.mp4")            # 无音轨
    e = os.path.join(tmp, "s5_short.mp4")
    make_clip(a, 320, 240, 30, 3.0, "red")
    make_clip(b, 480, 270, 25, 3.0, "green", tone=330)
    make_clip(c, 640, 360, 30, 3.0, "blue", tone=550)
    make_clip(d, 320, 240, 30, 2.0, "yellow", with_audio=False)
    make_clip(e, 320, 240, 30, 0.12, "white")          # 过短，测合并分支

    files = [a, b, c, d, e]
    entries = vv.entries_from_files(files)

    # 规格混杂必须能被检出
    check("检出帧率不一致", vv.plan_uniform_fps(entries) is not None,
          f"{vv.plan_uniform_fps(entries)}")
    check("检出分辨率不一致", vv.plan_uniform_size(entries)[0] is not None,
          f"{vv.plan_uniform_size(entries)}")
    check("检出无音轨素材", vv.has_audio(d) is False)

    # ---- N=1（单段，无转场）----
    out1 = os.path.join(tmp, "out_n1.mp4")
    vv.build_timeline([{"file": a, "start": 0, "end": 3.0}], out1, None, 0.0, "无")
    d1 = vv.probe_duration(out1)
    check("N=1 拼接成功", abs(d1 - 3.0) < 0.2, f"{d1:.2f}s")

    # ---- N=2（叠化 0.25 → 总长 = 3+3-0.25）----
    out2 = os.path.join(tmp, "out_n2.mp4")
    vv.build_timeline([{"file": a, "start": 0, "end": 3.0},
                       {"file": b, "start": 0, "end": 3.0}], out2, None, 0.25, "叠化")
    d2 = vv.probe_duration(out2)
    check("N=2 叠化时长正确", abs(d2 - 5.75) < 0.25, f"{d2:.2f}s（期望 5.75）")

    # ---- N=5（含无音轨 + 过短段；分辨率帧率混杂）----
    out5 = os.path.join(tmp, "out_n5.mp4")
    fps_u = vv.plan_uniform_fps(entries)
    w_u, h_u = vv.plan_uniform_size(entries)
    lens = [x["end"] - x["start"] for x in entries]
    bounds = vm.seg_bounds_of(lens, 0.25)
    vv.build_timeline(entries, out5, None, 0.25, "叠化", None, False,
                      18, "ultrafast", w_u, h_u, fps_u)
    d5 = vv.probe_duration(out5)
    expect = sum(lens) - 0.25 * (len(entries) - 1)
    check("N=5 拼接成功（含无音轨段）", abs(d5 - expect) < 0.5,
          f"{d5:.2f}s（期望 {expect:.2f}s）")
    check("N=5 段边界数量正确", len(bounds) == len(entries),
          f"{len(bounds)} 段：" + " ".join(f"{s:.1f}" for s, _ in bounds))

    # ---- 硬切（无转场）时长应无损 ----
    out0 = os.path.join(tmp, "out_hardcut.mp4")
    vv.build_timeline([{"file": a, "start": 0, "end": 3.0},
                       {"file": b, "start": 0, "end": 3.0}], out0, None, 0.0, "无",
                      out_w=1080, out_h=1920, fps=None)
    d0 = vv.probe_duration(out0)
    check("硬切时长无损", abs(d0 - 6.0) < 0.2, f"{d0:.2f}s（期望 6.00）")

    # ---- 色温对齐能收敛 ----
    cols = vv.measure_entries_colors(entries)
    gains = vv.compute_gains(cols)
    check("色温增益在限幅内", all(0.8 <= g[i] <= 1.2 for g in gains for i in range(3)))
    check("增益段数与段数一致", len(gains) == len(entries))


def main():
    tmp = tempfile.mkdtemp(prefix="vskill_selftest_")
    print("=" * 70)
    print("技能自检")
    print("=" * 70)
    print(f"  ffmpeg: {FFMPEG}")
    print(f"  临时目录: {tmp}")
    test_anchor()
    test_subs()
    test_map_time()
    test_merge()
    test_timeline(tmp)
    print("\n" + "=" * 70)
    print(f"通过 {len(PASS)} 项，失败 {len(FAIL)} 项")
    if FAIL:
        for n in FAIL:
            print(f"  ✗ {n}")
    else:
        # 本脚本只管「主流程逻辑」（锚点/换算/拼接）；其它模块各管一摊，改完对应代码单独跑
        print("其它模块的自检入口：")
        print("  python md_spec.py --selftest            文案 MD 解析（版本/卡片/背景音乐）")
        print("  python video_bgm.py --selftest          BGM 57 项（含 ffmpeg 真实混音 + 压低包络）")
        print("  python video_asr.py --selftest-align    文案对齐（不跑模型）")
        print("  python video_audio.py --presets         音频预设与默认值")
        print("  python video_build_ass.py --selftest    字幕折行与标色")
        print("  python video_visual.py --probe 素材.mp4 画面分段与色温量测")
    print("=" * 70)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
