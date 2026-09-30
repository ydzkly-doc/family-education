param(
    [string]$Background = (Join-Path $PSScriptRoot '底图_HZYJSJ_第01篇_封面_v01.png'),
    [string]$Output = (Join-Path $PSScriptRoot 'HZYJSJ_孩子与手机_第01篇_卡片_01_封面_v01.jpg')
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

function New-RoundedPath {
    param([float]$X, [float]$Y, [float]$Width, [float]$Height, [float]$Radius)
    $path = [System.Drawing.Drawing2D.GraphicsPath]::new()
    $d = $Radius * 2
    $path.AddArc($X, $Y, $d, $d, 180, 90)
    $path.AddArc($X + $Width - $d, $Y, $d, $d, 270, 90)
    $path.AddArc($X + $Width - $d, $Y + $Height - $d, $d, $d, 0, 90)
    $path.AddArc($X, $Y + $Height - $d, $d, $d, 90, 90)
    $path.CloseFigure()
    return $path
}

function New-FitFont {
    param(
        [System.Drawing.Graphics]$Graphics,
        [string]$Text,
        [string]$Family,
        [float]$StartSize,
        [float]$MinSize,
        [float]$MaxWidth,
        [System.Drawing.FontStyle]$Style = [System.Drawing.FontStyle]::Regular
    )
    for ($size = $StartSize; $size -ge $MinSize; $size -= 1) {
        $font = [System.Drawing.Font]::new($Family, $size, $Style, [System.Drawing.GraphicsUnit]::Pixel)
        $measure = $Graphics.MeasureString($Text, $font)
        if ($measure.Width -le $MaxWidth) { return $font }
        $font.Dispose()
    }
    return [System.Drawing.Font]::new($Family, $MinSize, $Style, [System.Drawing.GraphicsUnit]::Pixel)
}

$source = [System.Drawing.Image]::FromFile($Background)
$canvas = [System.Drawing.Bitmap]::new(1242, 1656, [System.Drawing.Imaging.PixelFormat]::Format24bppRgb)
$canvas.SetResolution(96, 96)
$g = [System.Drawing.Graphics]::FromImage($canvas)
$g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
$g.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
$g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
$g.DrawImage($source, 0, 0, 1242, 1656)

$fontFamily = 'Microsoft YaHei UI'
$deepGreen = [System.Drawing.Color]::FromArgb(255, 47, 78, 75)
$blueGray = [System.Drawing.Color]::FromArgb(255, 73, 91, 101)
$amber = [System.Drawing.Color]::FromArgb(255, 190, 128, 65)
$ivory = [System.Drawing.Color]::FromArgb(255, 250, 246, 235)

# Top series ribbon
$topPath = New-RoundedPath -X 72 -Y 76 -Width 1098 -Height 154 -Radius 24
$topBrush = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(235, 47, 78, 75))
$g.FillPath($topBrush, $topPath)

$center = [System.Drawing.StringFormat]::new()
$center.Alignment = [System.Drawing.StringAlignment]::Center
$center.LineAlignment = [System.Drawing.StringAlignment]::Center
$seriesText = '孩子与手机：从冲突管控到自主使用'
$seriesFont = New-FitFont -Graphics $g -Text $seriesText -Family $fontFamily -StartSize 38 -MinSize 30 -MaxWidth 930 -Style ([System.Drawing.FontStyle]::Bold)
$whiteBrush = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::White)
$g.DrawString($seriesText, $seriesFont, $whiteBrush, [System.Drawing.RectangleF]::new(112, 96, 1018, 58), $center)
$pageFont = [System.Drawing.Font]::new($fontFamily, 28, [System.Drawing.FontStyle]::Regular, [System.Drawing.GraphicsUnit]::Pixel)
$g.DrawString('第 1 篇 · 共 10 篇', $pageFont, $whiteBrush, [System.Drawing.RectangleF]::new(112, 158, 1018, 42), $center)

# Quiet reading panel: light enough to preserve the approved airy tone.
$panelPath = New-RoundedPath -X 102 -Y 292 -Width 1038 -Height 850 -Radius 34
$panelBrush = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(216, 250, 246, 235))
$panelPen = [System.Drawing.Pen]::new([System.Drawing.Color]::FromArgb(135, 69, 91, 89), 2)
$g.FillPath($panelBrush, $panelPath)
$g.DrawPath($panelPen, $panelPath)

$title1Font = New-FitFont -Graphics $g -Text '孩子爱玩手机，' -Family $fontFamily -StartSize 82 -MinSize 66 -MaxWidth 880 -Style ([System.Drawing.FontStyle]::Bold)
$title2Font = New-FitFont -Graphics $g -Text '不等于手机成瘾' -Family $fontFamily -StartSize 88 -MinSize 68 -MaxWidth 900 -Style ([System.Drawing.FontStyle]::Bold)
$deepBrush = [System.Drawing.SolidBrush]::new($deepGreen)
$amberBrush = [System.Drawing.SolidBrush]::new($amber)
$g.DrawString('孩子爱玩手机，', $title1Font, $deepBrush, [System.Drawing.RectangleF]::new(158, 424, 926, 118), $center)
$g.DrawString('不等于手机成瘾', $title2Font, $amberBrush, [System.Drawing.RectangleF]::new(158, 548, 926, 126), $center)

$linePen = [System.Drawing.Pen]::new([System.Drawing.Color]::FromArgb(220, 190, 128, 65), 5)
$g.DrawLine($linePen, 482, 724, 760, 724)

$subtitleFont = New-FitFont -Graphics $g -Text '先看功能影响，再谈怎么管' -Family $fontFamily -StartSize 46 -MinSize 38 -MaxWidth 850
$blueBrush = [System.Drawing.SolidBrush]::new($blueGray)
$g.DrawString('先看功能影响，再谈怎么管', $subtitleFont, $blueBrush, [System.Drawing.RectangleF]::new(168, 772, 906, 80), $center)

$noteFont = [System.Drawing.Font]::new($fontFamily, 30, [System.Drawing.FontStyle]::Regular, [System.Drawing.GraphicsUnit]::Pixel)
$noteBrush = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(255, 95, 105, 104))
$g.DrawString('先判断，再行动；先理解，再立规则', $noteFont, $noteBrush, [System.Drawing.RectangleF]::new(190, 936, 862, 58), $center)

# Bottom source/account strip
$bottomPath = New-RoundedPath -X 72 -Y 1398 -Width 1098 -Height 184 -Radius 24
$bottomBrush = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(238, 47, 78, 75))
$g.FillPath($bottomBrush, $bottomPath)
$sourceFont = [System.Drawing.Font]::new($fontFamily, 28, [System.Drawing.FontStyle]::Regular, [System.Drawing.GraphicsUnit]::Pixel)
$accountFont = [System.Drawing.Font]::new($fontFamily, 32, [System.Drawing.FontStyle]::Bold, [System.Drawing.GraphicsUnit]::Pixel)
$g.DrawString('课程学习心得 · 家庭场景改编', $sourceFont, $whiteBrush, [System.Drawing.RectangleF]::new(110, 1420, 1022, 54), $center)
$g.DrawString('归途有光·和孩子一起重启', $accountFont, $whiteBrush, [System.Drawing.RectangleF]::new(110, 1483, 1022, 62), $center)

$g.Dispose()
$source.Dispose()

$codec = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object MimeType -eq 'image/jpeg'
$qualityEncoder = [System.Drawing.Imaging.Encoder]::Quality
$saved = $false
foreach ($quality in 82, 76, 70, 64, 58, 52, 46, 40, 36, 32, 28, 24, 20) {
    $parameters = [System.Drawing.Imaging.EncoderParameters]::new(1)
    $parameters.Param[0] = [System.Drawing.Imaging.EncoderParameter]::new($qualityEncoder, [long]$quality)
    $stream = [System.IO.MemoryStream]::new()
    $canvas.Save($stream, $codec, $parameters)
    $bytes = $stream.ToArray()
    $stream.Dispose()
    $parameters.Dispose()
    if ($bytes.Length -lt 102400 -or $quality -eq 20) {
        [System.IO.File]::WriteAllBytes($Output, $bytes)
        Write-Output ("Saved {0} bytes at JPEG quality {1}" -f $bytes.Length, $quality)
        $saved = $true
        break
    }
}
$canvas.Dispose()

if (-not $saved) { throw 'Failed to save the cover sample.' }
