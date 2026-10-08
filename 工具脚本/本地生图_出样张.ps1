# 本地生图 · 出样张 v3
# 两个坑的绕法：
#   ① sd-cli.exe 写不进仓库内目录 -> 生成到仓库外，再用 PowerShell 拷进来
#   ② 中文文件名经 argv 传给 C++ 程序会被 GBK/UTF-8 双重编码搞坏 -> 生成时用 ASCII 名，拷贝时再改中文名
$ErrorActionPreference = 'Continue'

$root  = 'D:\local-imagegen'
$gen   = "$root\out"
$exe   = "$root\bin-vulkan\sd-cli.exe"
$model = "$root\models\DreamShaper8_LCM.safetensors"
$repo  = 'D:\个人资料\家庭教育\_tmp_imagegen'
$py    = 'C:\Users\ZhuanZ\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'

New-Item -ItemType Directory -Force -Path $gen, $repo | Out-Null
# 清掉上一轮被编码搞坏的文件名
Get-ChildItem $gen -File | Where-Object { $_.Name -notmatch '^[\x20-\x7E]+$' } | Remove-Item -Force -ErrorAction SilentlyContinue

$shots = @(
  @{ ascii = 'shot01_doorway';   cn = '01_封面_门缝光.png';   prompt = 'a warm doorway with soft golden light spilling through, quiet interior, muted earthy tones, cinematic soft lighting, minimal composition, no text, no letters, no watermark' },
  @{ ascii = 'shot02_windowsill'; cn = '02_卡片_窗边静物.png'; prompt = 'still life on a wooden windowsill, ceramic cup and a small plant, soft morning sunlight, calm muted colors, shallow depth of field, no text, no letters, no watermark' },
  @{ ascii = 'shot03_table';     cn = '03_卡片_木桌暖光.png'; prompt = 'a rustic wooden table in a quiet room, warm afternoon light through sheer curtains, empty space, cozy atmosphere, muted beige and brown, no text, no letters, no watermark' }
)

"=== 生成（Vulkan / 核显，失败自动重试一次）==="
foreach ($s in $shots) {
  $png = Join-Path $gen "$($s.ascii).png"
  for ($try = 1; $try -le 2; $try++) {
    Remove-Item $png -Force -ErrorAction SilentlyContinue
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    & $exe -m $model -p $s.prompt -W 512 -H 512 --steps 6 --cfg-scale 1.0 -s 12345 -o $png 2>&1 |
      Out-File (Join-Path $gen "log_$($s.ascii)_$try.txt") -Encoding UTF8
    $sw.Stop()
    if (Test-Path $png) {
      "  OK   {0}  第{1}次  {2:N1}s  {3} KB" -f $s.ascii, $try, $sw.Elapsed.TotalSeconds, [math]::Round((Get-Item $png).Length/1KB,1)
      break
    }
    "  重试 {0} 第{1}次失败（{2:N1}s）" -f $s.ascii, $try, $sw.Elapsed.TotalSeconds
  }
}

# --- 合成：2.35:1 封面 + 3:4 卡片底图（全 ASCII 输出名）---
$pyCode = @'
import os
from PIL import Image, ImageFilter, ImageEnhance
gen = r"D:\local-imagegen\out"

def save_under(img, path, limit_kb, start_q=94):
    q = start_q
    while q >= 40:
        img.save(path, "JPEG", quality=q, optimize=True)
        if os.path.getsize(path) <= limit_kb * 1024:
            break
        q -= 4
    return q, os.path.getsize(path) // 1024

# 1) 2.35:1 封面：SOP 要求 核心意象居中方形安全区、两侧只放背景/留白
im = Image.open(os.path.join(gen, "shot01_doorway.png")).convert("RGB")
W, H = 1200, 511
canvas = Image.new("RGB", (W, H), (0, 0, 0))
bg = im.resize((W, max(H, int(W * im.height / im.width))), Image.LANCZOS)
bg = bg.crop((0, (bg.height - H)//2, W, (bg.height - H)//2 + H)).filter(ImageFilter.GaussianBlur(48))
canvas.paste(ImageEnhance.Brightness(bg).enhance(0.72), (0, 0))
canvas.paste(im.resize((H, H), Image.LANCZOS), ((W - H)//2, 0))
q, kb = save_under(canvas, os.path.join(gen, "cover_235x1.jpg"), 200)
print("COVER_OK", canvas.size, kb, "KB", "q=", q)

# 2) 3:4 卡片底图：SOP 要求 底图一律柔化（否则压不进 100KB）
c = Image.open(os.path.join(gen, "shot02_windowsill.png")).convert("RGB")
cw, ch = 900, 1200
cb = c.resize((cw, int(cw * c.height / c.width)), Image.LANCZOS)
cb = cb.crop((0, (cb.height - ch)//2, cw, (cb.height - ch)//2 + ch))
cb = ImageEnhance.Brightness(cb.filter(ImageFilter.GaussianBlur(6))).enhance(0.85)
q, kb = save_under(cb, os.path.join(gen, "card_3x4.jpg"), 100, start_q=88)
print("CARD_OK", cb.size, kb, "KB", "q=", q)
'@
$pyFile = Join-Path $gen 'compose.py'
[System.IO.File]::WriteAllText($pyFile, $pyCode, (New-Object System.Text.UTF8Encoding($false)))
"`n=== 合成 ==="
& $py $pyFile 2>&1 | ForEach-Object { "  $_" }

# --- 用 PowerShell 拷进仓库并改成中文名（PowerShell 处理 Unicode 没问题）---
"`n=== 拷入仓库 ==="
$map = @{
  'shot01_doorway.png'   = '01_封面_门缝光.png'
  'shot02_windowsill.png'= '02_卡片_窗边静物.png'
  'shot03_table.png'     = '03_卡片_木桌暖光.png'
  'cover_235x1.jpg'      = '封面_235x1_成品.jpg'
  'card_3x4.jpg'         = '卡片底图_3x4_柔化.jpg'
}
foreach ($k in $map.Keys) {
  $s = Join-Path $gen $k
  if (Test-Path $s) { Copy-Item $s (Join-Path $repo $map[$k]) -Force; "  拷入 $($map[$k])" } else { "  缺 $k" }
}
Get-ChildItem $repo -File | Where-Object { $_.Extension -in '.png','.jpg' } |
  Select-Object Name, @{n='KB';e={[math]::Round($_.Length/1KB,1)}} | Format-Table -AutoSize
"DONE"
