$output = Join-Path $PSScriptRoot '..\outputs'
$indexPath = Join-Path $output 'index.html'
$singlePath = Join-Path $output 'jinggangshan-miniapp-prototype.html'
$index = Get-Content -LiteralPath $indexPath -Raw -Encoding UTF8

$heroBytes = [System.IO.File]::ReadAllBytes((Join-Path $output 'jinggangshan-hero.png'))
$heroData = 'data:image/png;base64,' + [Convert]::ToBase64String($heroBytes)
$customStickerPath = Join-Path $output 'assets\stickers\custom\red-soldier-custom-received.png'
$customStickerData = 'data:image/png;base64,' + [Convert]::ToBase64String([System.IO.File]::ReadAllBytes($customStickerPath))
$customSteadyPath = Join-Path $output 'assets\stickers\custom\red-soldier-custom-steady.png'
$customSteadyData = 'data:image/png;base64,' + [Convert]::ToBase64String([System.IO.File]::ReadAllBytes($customSteadyPath))

$embeddedStickers = @{}
Get-ChildItem -LiteralPath (Join-Path $output 'assets\stickers') -Directory | Where-Object { $_.Name -in @('red-soldier', 'red-bugle', 'red-torch', 'bamboo-rice') } | ForEach-Object {
  $set = @()
  Get-ChildItem -LiteralPath $_.FullName -Filter '*.png' | Sort-Object Name | ForEach-Object {
    $set += 'data:image/png;base64,' + [Convert]::ToBase64String([System.IO.File]::ReadAllBytes($_.FullName))
  }
  $embeddedStickers[$_.Name] = $set
}

$knowledgeBase = Get-Content -LiteralPath (Join-Path $output 'assets\jinggangshan-knowledge-base.json') -Raw -Encoding UTF8
$offlineScript = '<script>window.__JGS_STICKER_SOURCES__=' + ($embeddedStickers | ConvertTo-Json -Compress -Depth 4) + ';window.__JGS_KNOWLEDGE_BASE__=' + $knowledgeBase + ';</script>'
$single = $index.Replace('jinggangshan-hero.png', $heroData).Replace('assets/stickers/custom/red-soldier-custom-received.png', $customStickerData).Replace('assets/stickers/custom/red-soldier-custom-steady.png', $customSteadyData).Replace('</head>', $offlineScript + '</head>')
Set-Content -LiteralPath $singlePath -Value $single -Encoding UTF8 -NoNewline

Push-Location $output
Compress-Archive -Path index.html,jinggangshan-miniapp-prototype.html,jinggangshan-hero.png,jinggangshan-agent-api-example.mjs,jinggangshan-agent-api-example.py,AI-STICKER-SETUP.md,START-JGS-MINIAPP.ps1,.env.local.example,assets -DestinationPath jinggangshan-miniapp-prototype.zip -Force
Pop-Location
