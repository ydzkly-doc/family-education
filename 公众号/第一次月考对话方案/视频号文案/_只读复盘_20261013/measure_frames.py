import json
from pathlib import Path
from PIL import Image, ImageStat

OUT = Path(r"D:\个人资料\家庭教育\公众号\第一次月考对话方案\视频号文案\_只读复盘_20261013")
FR = OUT / "frames"

# 基于目检的近似区域：人物脸部、背景亮窗/墙面、字幕带。
REGIONS = {
    "face": (300, 760, 780, 1330),
    "face_shadow_left": (330, 800, 540, 1260),
    "face_center": (430, 780, 700, 1280),
    "bright_window": (390, 350, 650, 760),
    "subtitle_band": (80, 1250, 1000, 1510),
    "top_hook_band": (80, 420, 1000, 760),
}

rows = []
for d in sorted(FR.iterdir()):
    if not d.is_dir():
        continue
    for imgp in sorted(d.glob("*.jpg")):
        im = Image.open(imgp).convert("RGB")
        gray = im.convert("L")
        row = {"id": d.name, "file": imgp.name, "size": im.size}
        for name, box in REGIONS.items():
            crop = gray.crop(box)
            st = ImageStat.Stat(crop)
            hist = crop.histogram()
            total = sum(hist)
            # percentile helper
            def pct(p):
                target = total * p
                acc = 0
                for i, v in enumerate(hist):
                    acc += v
                    if acc >= target:
                        return i
                return 255
            row[name] = {
                "mean": round(st.mean[0], 1),
                "p05": pct(0.05),
                "p25": pct(0.25),
                "p50": pct(0.50),
                "p75": pct(0.75),
                "p95": pct(0.95),
            }
        rows.append(row)

(OUT / "frame_light_metrics.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
# 打印关键时点：2.2秒（封面卡后）、中段、90%处
lines = []
for r in rows:
    if any(x in r["file"] for x in ["0002.20", "050", "075", "090"]):
        lines.append(f"{r['id']} {r['file']} face p25/p50/p95={r['face']['p25']}/{r['face']['p50']}/{r['face']['p95']} mean={r['face']['mean']} | window p50/p95={r['bright_window']['p50']}/{r['bright_window']['p95']}")
(OUT / "frame_light_metrics_key.txt").write_text("\n".join(lines), encoding="utf-8")
print("\n".join(lines))
