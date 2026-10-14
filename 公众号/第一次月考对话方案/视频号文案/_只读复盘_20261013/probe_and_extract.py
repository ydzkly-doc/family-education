import json
import subprocess
from pathlib import Path

FFMPEG = r"C:\Users\ZhuanZ\.workbuddy\binaries\ffmpeg\bin\ffmpeg.exe"
FFPROBE = r"C:\Users\ZhuanZ\.workbuddy\binaries\ffmpeg\bin\ffprobe.exe"
BASE = Path(r"D:\个人资料\家庭教育\公众号\第一次月考对话方案\视频号文案")
OUT = BASE / "_只读复盘_20261013"
FRAMES = OUT / "frames"
AUDIO = OUT / "audio"

ITEMS = [
    ("01", "01_出分前忍住别问"),
    ("02", "02_我不是那块料"),
    ("03", "03_考好别泼冷水"),
    ("04", "04_火上来先离开"),
    ("05", "05_家长会"),
]


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout, p.stderr


def probe(path: Path):
    cmd = [
        FFPROBE, "-v", "error",
        "-show_format",
        "-show_streams",
        "-of", "json",
        str(path),
    ]
    rc, out, err = run(cmd)
    if rc != 0:
        return {"error": err}
    return json.loads(out)


def summarize_probe(data):
    fmt = data.get("format", {})
    rows = []
    result = {
        "file": fmt.get("filename"),
        "duration": float(fmt.get("duration", 0) or 0),
        "size": int(fmt.get("size", 0) or 0),
        "bit_rate": int(fmt.get("bit_rate", 0) or 0),
        "format": fmt.get("format_name"),
        "streams": rows,
    }
    for s in data.get("streams", []):
        row = {
            "codec_type": s.get("codec_type"),
            "codec_name": s.get("codec_name"),
            "start_time": float(s.get("start_time", 0) or 0),
            "duration": float(s.get("duration", 0) or 0),
            "end_time": float(s.get("start_time", 0) or 0) + float(s.get("duration", 0) or 0),
            "bit_rate": int(s.get("bit_rate", 0) or 0),
        }
        if s.get("codec_type") == "video":
            row.update({
                "width": s.get("width"),
                "height": s.get("height"),
                "r_frame_rate": s.get("r_frame_rate"),
                "avg_frame_rate": s.get("avg_frame_rate"),
                "profile": s.get("profile"),
                "level": s.get("level"),
                "pix_fmt": s.get("pix_fmt"),
            })
        if s.get("codec_type") == "audio":
            row.update({
                "sample_rate": s.get("sample_rate"),
                "channels": s.get("channels"),
                "channel_layout": s.get("channel_layout"),
            })
        rows.append(row)
    return result


def loudnorm(path: Path, key: str):
    log = AUDIO / f"{key}_loudnorm.txt"
    cmd = [
        FFMPEG, "-hide_banner", "-nostats", "-i", str(path),
        "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=summary",
        "-f", "null", "-"
    ]
    rc, out, err = run(cmd)
    text = (out or "") + "\n[stderr]\n" + (err or "")
    log.write_text(text, encoding="utf-8")
    return log


def volumedetect(path: Path, key: str):
    log = AUDIO / f"{key}_volumedetect.txt"
    cmd = [
        FFMPEG, "-hide_banner", "-nostats", "-i", str(path),
        "-af", "volumedetect",
        "-f", "null", "-"
    ]
    rc, out, err = run(cmd)
    text = (out or "") + "\n[stderr]\n" + (err or "")
    log.write_text(text, encoding="utf-8")
    return log


def astats(path: Path, key: str):
    log = AUDIO / f"{key}_astats.txt"
    cmd = [
        FFMPEG, "-hide_banner", "-nostats", "-i", str(path),
        "-map", "a:0",
        "-af", "astats=metadata=1:reset=1",
        "-f", "null", "-"
    ]
    rc, out, err = run(cmd)
    text = (out or "") + "\n[stderr]\n" + (err or "")
    log.write_text(text, encoding="utf-8")
    return log


def extract_frames(path: Path, key: str, duration: float):
    d = FRAMES / key
    d.mkdir(parents=True, exist_ok=True)
    # 0.1 秒看封面卡；0.3/2.2 秒看封面与正片交接；其余按比例看构图、字幕、结尾。
    times = [0.1, 0.3, 2.2, max(3.0, duration * 0.10), duration * 0.25,
             duration * 0.50, duration * 0.75, duration * 0.90, max(0.0, duration - 1.5)]
    times = sorted(set(round(t, 2) for t in times if 0 <= t < duration))
    made = []
    for t in times:
        out = d / f"{key}_t{t:07.2f}.jpg"
        cmd = [
            FFMPEG, "-v", "error",
            "-ss", f"{t:.3f}", "-i", str(path),
            "-frames:v", "1", "-q:v", "2",
            str(out), "-y"
        ]
        rc, so, se = run(cmd)
        if rc == 0 and out.exists():
            made.append(str(out))
        else:
            made.append(f"FAIL t={t}: {se.strip()[:200]}")
    return times, made


def main():
    FRAMES.mkdir(parents=True, exist_ok=True)
    AUDIO.mkdir(parents=True, exist_ok=True)
    summaries = []
    for key, dirname in ITEMS:
        path = BASE / dirname / "_成品" / f"成片_{key}.mp4"
        data = probe(path)
        summary = summarize_probe(data)
        summaries.append(summary)
        loudnorm(path, key)
        volumedetect(path, key)
        astats(path, key)
        times, made = extract_frames(path, key, summary["duration"])
        summary["sample_times"] = times
        summary["frames"] = made
    (OUT / "probe_summary.json").write_text(json.dumps(summaries, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = []
    for s in summaries:
        lines.append(f"## {Path(s['file']).parent.parent.name}")
        lines.append(f"duration={s['duration']:.3f}s size={s['size']/1024/1024:.1f}MiB bitrate={s['bit_rate']/1000:.0f}kbps")
        for st in s["streams"]:
            if st["codec_type"] == "video":
                lines.append("V {width}x{height} {codec_name} {profile} level={level} fps={avg_frame_rate} start={start_time:.3f} dur={duration:.3f} end={end_time:.3f} br={bit_rate}".format(**st))
            elif st["codec_type"] == "audio":
                lines.append("A {codec_name} {sample_rate}Hz {channels}ch start={start_time:.3f} dur={duration:.3f} end={end_time:.3f} br={bit_rate}".format(**st))
        lines.append("frames=" + ",".join(str(x) for x in s["sample_times"]))
        lines.append("")
    (OUT / "probe_summary.txt").write_text("\n".join(lines), encoding="utf-8")
    print((OUT / "probe_summary.txt").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
