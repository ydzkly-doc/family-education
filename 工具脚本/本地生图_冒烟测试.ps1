# 本地文生图 · 冒烟测试 v2（修掉原生命令 stderr 被当成终止错误的问题）
$root  = 'D:\local-imagegen'
$model = "$root\models\DreamShaper8_LCM.safetensors"
$out   = 'D:\个人资料\家庭教育\_tmp_imagegen'
New-Item -ItemType Directory -Force -Path $out | Out-Null
"OUT = $out"

# 关键：原生 exe 会把日志写到 stderr，必须放宽 ErrorActionPreference，否则被当异常中断
$saved = $ErrorActionPreference
$ErrorActionPreference = 'Continue'

$prompt = 'still life, a warm ceramic cup on a rustic wooden table beside a sunlit window, soft morning light, muted earthy colors, shallow depth of field, minimal, no text'

$exeCpu = "$root\bin-cpu\sd-cli.exe"
$exeVk  = "$root\bin-vulkan\sd-cli.exe"

# --- 先确认参数名（不同版本有差异）---
"`n=== 相关参数 ==="
(& $exeCpu --help 2>&1 | Out-String) -split "`n" |
  Where-Object { $_ -match 'steps|cfg|sampling|scheduler|lcm|seed|batch|\-W|\-H' } |
  ForEach-Object { $_.TrimEnd() } | Select-Object -First 30

# --- 逐个构建出图并计时 ---
$jobs = [ordered]@{ 'cpu' = $exeCpu; 'vulkan' = $exeVk }
foreach ($kind in $jobs.Keys) {
  $exe = $jobs[$kind]
  if (-not (Test-Path $exe)) { "跳过 $kind"; continue }
  $png = Join-Path $out "smoke_$kind.png"
  $log = Join-Path $out "log_$kind.txt"
  Remove-Item $png, $log -Force -ErrorAction SilentlyContinue

  "`n--- [$kind] ---"
  $sw = [System.Diagnostics.Stopwatch]::StartNew()
  & $exe -m $model -p $prompt -W 512 -H 512 --steps 6 --cfg-scale 1.0 -s 42 -o $png 2>&1 |
    Out-File -FilePath $log -Encoding UTF8
  $sw.Stop()

  Get-Content $log -Tail 8 | ForEach-Object { "    $_" }
  if (Test-Path $png) {
    "  ✅ OK  {0:N1} 秒/张  ({1} KB)" -f $sw.Elapsed.TotalSeconds, [math]::Round((Get-Item $png).Length / 1KB, 1)
  } else {
    "  ❌ FAIL  用时 {0:N1} 秒" -f $sw.Elapsed.TotalSeconds
  }
}

$ErrorActionPreference = $saved
"`nDONE"
