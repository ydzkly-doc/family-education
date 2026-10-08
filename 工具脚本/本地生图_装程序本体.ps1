# 本地文生图 · 程序本体安装 + 冒烟测试（修正版）
# 修正点：上一版过滤文件名含 "win"，把 DarWIN（macOS）也匹配进去了。
# 现在用 "-win-" 做判别，并同时装 CPU 版与 Vulkan 版（核显可加速），跑完对比速度。
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$ProgressPreference = 'SilentlyContinue'

$root  = 'D:\local-imagegen'
$model = "$root\models\DreamShaper8_LCM.safetensors"
if (-not (Test-Path $model)) { throw "模型不存在：$model" }
"MODEL = $model  ({0} GB)" -f [math]::Round((Get-Item $model).Length / 1GB, 2)

# --- 清掉上一版误装的 macOS 二进制 ---
Get-ChildItem "$root\bin" -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "$root\sd-cpp.zip" -Force -ErrorAction SilentlyContinue

# --- 取正确的 Windows 包 ---
$rel = Invoke-RestMethod 'https://api.github.com/repos/leejet/stable-diffusion.cpp/releases/latest' `
  -Headers @{ 'User-Agent' = 'dsh-imagegen-setup' }
$wins = @($rel.assets | Where-Object { $_.name -match '(?i)-win-' })
"`nWindows 包："
$wins | ForEach-Object { "  {0}  {1} MB" -f $_.name, [math]::Round($_.size / 1MB, 1) }

$builds = @{}
foreach ($kind in @('win-cpu', 'win-vulkan')) {
  $a = $wins | Where-Object { $_.name -match [regex]::Escape($kind) } | Select-Object -First 1
  if (-not $a) { "  跳过 $kind（无此包）"; continue }
  $dir = "$root\bin-$($kind -replace '^win-', '')"
  New-Item -ItemType Directory -Force -Path $dir | Out-Null
  $z = "$root\$kind.zip"
  if (-not (Test-Path $z)) { "  下载 $($a.name) ..."; Invoke-WebRequest $a.browser_download_url -OutFile $z -UseBasicParsing }
  Expand-Archive $z -DestinationPath $dir -Force
  $exe = Get-ChildItem $dir -Recurse -Filter 'sd.exe' -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($exe) { $builds[$kind] = $exe.FullName; "  OK  $kind -> $($exe.FullName)" }
  else { "  ⚠ $kind 展开后没找到 sd.exe" }
}
if ($builds.Count -eq 0) { throw '两个包都没拿到 sd.exe' }

# --- 先看命令行参数（不同版本 flag 会变）---
$cpu = $builds['win-cpu']
if ($cpu) {
  "`n=== sd.exe --help ==="
  & $cpu --help 2>&1 | Select-Object -First 60
}

# --- 冒烟测试：每个构建各出一张，计时 ---
$prompt = 'still life, a warm ceramic cup on a wooden table by a sunlit window, soft morning light, muted colors, shallow depth of field, no text'
foreach ($kind in $builds.Keys) {
  $exe = $builds[$kind]
  $out = "$root\out\smoke_$kind.png"
  Remove-Item $out -Force -ErrorAction SilentlyContinue
  "`n=== 冒烟测试 [$kind] ==="
  $err = $null
  $secs = (Measure-Command {
    try {
      & $exe -m $model -p $prompt -W 512 -H 512 --steps 6 --cfg-scale 1.0 -o $out -v 2>&1 |
        Select-Object -Last 12
    } catch { $err = $_ }
  }).TotalSeconds
  if ($err) { "  异常: $($err.Exception.Message)" }
  if (Test-Path $out) {
    "  ✅ OK  $kind  {0:N1} 秒/张  ->  $out  ({1} KB)" -f $secs, [math]::Round((Get-Item $out).Length / 1KB, 1)
  } else {
    "  ❌ FAIL $kind  用时 {0:N1} 秒（未产出图片）" -f $secs
  }
}
"`nDONE"
