# -*- coding: utf-8 -*-
"""05 条尾部静音回潮修复：

现状（2026-10-14）：成片_05.mp4 = 143.88s，音轨只到 134.70s，尾部 9.18s 有画无声。
根因：素材 03.MOV 音轨只到 43.42s（视频 52.74s）。2026-10-04 曾手工截到 134.700s，
      但 2026-10-11 重烧片头时用的是未截断的无封面卡旧源，静音尾又被带回。
修法（与 10-04 一致）：流拷贝无损截断到音轨结束时刻（-t 134.700 -c copy），
      新片头 2.0s 封面卡保留不动。
"""
import json
import os
import shutil
import subprocess

FFPROBE = r"C:/Users/ZhuanZ/.workbuddy/binaries/ffmpeg/bin/ffprobe.exe"
FFMPEG = r"C:/Users/ZhuanZ/.workbuddy/binaries/ffmpeg/bin/ffmpeg.exe"

DST = r"D:/个人资料/家庭教育/公众号/改善你的亲子关系/视频号文案/05_对同事客客气气回家只剩命令/_成品/成片_05.mp4"
BAK = os.path.join(os.path.dirname(DST), "_旧版本", "成片_05_含静音尾9.2s_20261014.mp4")
CUT = 134.700  # 音轨结束时刻（与 10-04 手工值一致）
TMP = DST + ".trimtmp.mp4"


def dur(path, stream=None):
    args = [FFPROBE, "-v", "error", "-show_entries",
            (f"stream={stream}:" if stream else "") + "duration",
            "-of", "csv=p=0", path]
    # 上面拼法对 select_streams 不适用，直接用 -select_streams
    if stream:
        args = [FFPROBE, "-v", "error", "-select_streams", stream,
                "-show_entries", "stream=duration", "-of", "csv=p=0", path]
    else:
        args = [FFPROBE, "-v", "error", "-show_entries", "format=duration",
                "-of", "csv=p=0", path]
    return float(subprocess.run(args, capture_output=True, text=True).stdout.strip())


def main():
    before = dur(DST)
    abefore = dur(DST, "a:0")
    print(f"截断前：容器 {before:.3f}s  音频 {abefore:.3f}s  差 {before - abefore:.3f}s")
    assert before - abefore > 5, "异常：本片没有明显尾部缺音，拒绝处理"

    os.makedirs(os.path.dirname(BAK), exist_ok=True)
    if not os.path.exists(BAK):
        shutil.copy2(DST, BAK)
        print(f"已备份现片 → {BAK}")
    else:
        print(f"备份已存在，跳过：{BAK}")

    # 无损流拷贝：从 0 截到 CUT（封面卡在 0~2s，保留）
    cmd = [FFMPEG, "-y", "-i", DST, "-t", f"{CUT:.3f}",
           "-map", "0", "-c", "copy", "-avoid_negative_ts", "make_zero", TMP]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print(r.stderr[-2000:])
        raise SystemExit("ffmpeg 截断失败")

    after_f = dur(TMP)
    after_a = dur(TMP, "a:0")
    after_v = dur(TMP, "v:0")
    print(f"截断后：容器 {after_f:.3f}s  视频 {after_v:.3f}s  音频 {after_a:.3f}s")
    assert abs(after_f - CUT) < 0.2, "截断后时长不符"
    assert abs(after_f - after_a) < 0.2, "截断后音视频仍不齐"

    os.replace(TMP, DST)
    print(f"已覆盖 → {DST}")

    # cover.json 保持不变（片头仍是 2.0s 封面卡）
    cj = DST + ".cover.json"
    if os.path.exists(cj):
        print("cover.json 保留：", json.load(open(cj, encoding="utf-8")))


if __name__ == "__main__":
    main()
