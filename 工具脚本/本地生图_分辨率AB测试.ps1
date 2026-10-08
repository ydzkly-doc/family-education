# 512 vs 768 生成分辨率 A/B 测试
# 同一提示词、同一种子，只改 --size，比较封面成品的清晰度
$ErrorActionPreference = 'Continue'
$root = 'D:\个人资料\家庭教育'
$py   = 'C:\Users\ZhuanZ\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'
$gen  = "$root\工具脚本\本地生图_生成.py"
$out  = "$root\_tmp_imagegen"

$prompt = "a warm doorway with soft golden light spilling through, quiet interior, muted earthy tones, cinematic soft lighting, minimal composition, no text, no letters, no watermark"
$seed = 777

foreach ($size in @(512, 768)) {
  "=== --size $size ==="
  $sw = [System.Diagnostics.Stopwatch]::StartNew()
  & $py $gen --prompt $prompt --preset cover --size $size --seed $seed `
      --out "$out\AB_cover_$size.jpg" --json 2>&1 | Out-String | Write-Output
  "  墙钟耗时 {0:N1}s" -f $sw.Elapsed.TotalSeconds
}

# --- 拼一张左右对照图：各取封面中央 511x511 方形安全区 ---
$pyCode = @'
import os
from PIL import Image
out = r"D:\个人资料\家庭教育\_tmp_imagegen"
panels = []
for size in (512, 768):
    p = os.path.join(out, f"AB_cover_{size}.jpg")
    if not os.path.exists(p):
        print("MISSING", p); continue
    im = Image.open(p).convert("RGB")
    x = (im.width - 511) // 2
    panels.append(im.crop((x, 0, x + 511, 511)))
if len(panels) == 2:
    W = 511 * 2 + 6
    canvas = Image.new("RGB", (W, 511), (255, 255, 255))
    canvas.paste(panels[0], (0, 0))
    canvas.paste(panels[1], (517, 0))
    dst = os.path.join(out, "AB_中央对照_左512_右768.jpg")
    canvas.save(dst, "JPEG", quality=96)
    print("PANEL_OK", dst, canvas.size, os.path.getsize(dst) // 1024, "KB")
'@
$pf = "$out\ab_panel.py"
[System.IO.File]::WriteAllText($pf, $pyCode, (New-Object System.Text.UTF8Encoding($false)))
"`n=== 拼接对照图 ==="
& $py $pf 2>&1 | ForEach-Object { "  $_" }

"`n=== 产物 ==="
Get-ChildItem $out -File | Where-Object { $_.Name -like 'AB_*' } |
  Select-Object Name, @{n='KB';e={[math]::Round($_.Length/1KB,1)}} | Format-Table -AutoSize
"DONE"
