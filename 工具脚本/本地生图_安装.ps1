# 本地文生图环境安装脚本（stable-diffusion.cpp）
# 目标：给 DSH 提供 ffmpeg 式的本地生图能力——独立 exe + 模型文件，不要账号、不联网推理。
# 目录固定在 D:\local-imagegen\（刻意放在仓库外：模型 2~4GB，不该进 git）
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$ProgressPreference = 'SilentlyContinue'

$root = 'D:\local-imagegen'
New-Item -ItemType Directory -Force -Path "$root\bin", "$root\models", "$root\out" | Out-Null
"ROOT = $root"

# ---------------------------------------------------------------- 1. 程序本体
"`n=== [1/3] 查询 stable-diffusion.cpp 最新 release ==="
$rel = Invoke-RestMethod 'https://api.github.com/repos/leejet/stable-diffusion.cpp/releases/latest' `
  -Headers @{ 'User-Agent' = 'dsh-imagegen-setup' }
"tag: $($rel.tag_name)"

$assets = @($rel.assets | Where-Object { $_.name -match '(?i)win' -and $_.name -match '\.zip$' })
if ($assets.Count -eq 0) { throw '未找到 Windows 资源包' }
$assets | ForEach-Object { "  asset: {0}  {1} MB" -f $_.name, [math]::Round($_.size / 1MB, 1) }

# 优先纯 CPU 的 AVX2 版（i5-1340P 支持 AVX2）；避开 cuda/rocm
$pick = $assets | Where-Object { $_.name -match '(?i)avx2' -and $_.name -notmatch '(?i)cuda|rocm' } | Select-Object -First 1
if (-not $pick) { $pick = $assets | Where-Object { $_.name -notmatch '(?i)cuda|rocm|vulkan' } | Select-Object -First 1 }
if (-not $pick) { $pick = $assets | Select-Object -First 1 }
"picked: $($pick.name)"

$zip = "$root\sd-cpp.zip"
if (-not (Test-Path $zip)) {
  "downloading ..."
  Invoke-WebRequest $pick.browser_download_url -OutFile $zip -UseBasicParsing
}
"zip size: {0} MB" -f [math]::Round((Get-Item $zip).Length / 1MB, 1)
Expand-Archive $zip -DestinationPath "$root\bin" -Force
"展开完成："
Get-ChildItem "$root\bin" -Recurse -File | Where-Object { $_.Extension -in '.exe', '.dll' } |
  Select-Object -First 20 -ExpandProperty FullName

# ---------------------------------------------------------------- 2. 模型
"`n=== [2/3] 下载模型（逐个候选尝试）==="
$candidates = @(
  @{ repo = 'Lykon/dreamshaper-8-lcm';                          file = 'DreamShaper8_LCM.safetensors' },
  @{ repo = 'stable-diffusion-v1-5/stable-diffusion-v1-5';      file = 'v1-5-pruned-emaonly.safetensors' },
  @{ repo = 'stabilityai/sd-turbo';                             file = 'sd_turbo.safetensors' }
)
$hosts = @('https://huggingface.co', 'https://hf-mirror.com')

$modelPath = $null
foreach ($c in $candidates) {
  foreach ($h in $hosts) {
    $url = "$h/$($c.repo)/resolve/main/$($c.file)"
    $dest = "$root\models\$($c.file)"
    if (Test-Path $dest) { $modelPath = $dest; break }
    try {
      "尝试 $url"
      Invoke-WebRequest $url -OutFile $dest -UseBasicParsing -TimeoutSec 600
      if ((Get-Item $dest).Length -gt 100MB) { $modelPath = $dest; "OK -> $dest"; break }
      else { "文件过小，丢弃"; Remove-Item $dest -Force }
    } catch {
      "失败: $($_.Exception.Message.Split([char]10)[0])"
      if (Test-Path $dest) { Remove-Item $dest -Force -ErrorAction SilentlyContinue }
    }
  }
  if ($modelPath) { break }
}
if (-not $modelPath) { throw '所有模型候选都下载失败' }
"model: $modelPath  ({0} GB)" -f [math]::Round((Get-Item $modelPath).Length / 1GB, 2)

# ---------------------------------------------------------------- 3. 冒烟测试
"`n=== [3/3] 冒烟测试 ==="
$exe = Get-ChildItem "$root\bin" -Recurse -Filter 'sd.exe' -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $exe) { throw '没找到 sd.exe' }
"exe: $($exe.FullName)"

$out = "$root\out\smoke.png"
& $exe.FullName -m $modelPath -p "a warm doorway with soft light, minimal, no text" `
  -W 512 -H 512 --steps 6 --cfg-scale 1.0 -o $out -v 2>&1 |
  Select-Object -Last 25

if (Test-Path $out) {
  $t = Measure-Command { }
  "SMOKE OK -> $out  ({0} KB)" -f [math]::Round((Get-Item $out).Length / 1KB, 1)
} else {
  "SMOKE FAILED：未生成图片"
}
"DONE"
