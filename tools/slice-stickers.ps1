Add-Type -AssemblyName System.Drawing

$sourceRoot = 'C:\Users\Ken\AppData\Local\Temp'
$outputRoot = Join-Path $PSScriptRoot '..\outputs\assets\stickers'
New-Item -ItemType Directory -Force -Path $outputRoot | Out-Null

$sets = @(
  @{ Slug = 'red-soldier'; Source = 'codex-clipboard-a00959d0-f92e-45c6-96cb-8a24e0dc0809.png'; Rows = 3 },
  @{ Slug = 'red-bugle'; Source = 'codex-clipboard-08ce02e9-d688-4837-9486-739374d0e913.png'; Rows = 4 },
  @{ Slug = 'red-torch'; Source = 'codex-clipboard-d2a85969-d895-4ba3-adbb-0dc102fcbbac.png'; Rows = 3 },
  @{ Slug = 'bamboo-rice'; Source = 'codex-clipboard-76aa1852-836c-47a6-a53a-cb0850879262.png'; Rows = 4 }
)

function Remove-BlueBackground([System.Drawing.Bitmap]$bitmap) {
  for ($y = 0; $y -lt $bitmap.Height; $y++) {
    for ($x = 0; $x -lt $bitmap.Width; $x++) {
      $pixel = $bitmap.GetPixel($x, $y)
      if ($pixel.B -gt 180 -and $pixel.G -gt 140 -and $pixel.B -gt ($pixel.R + 20) -and $pixel.G -gt $pixel.R) {
        $bitmap.SetPixel($x, $y, [System.Drawing.Color]::FromArgb(0, $pixel.R, $pixel.G, $pixel.B))
      }
    }
  }
}

foreach ($set in $sets) {
  $sourcePath = Join-Path $sourceRoot $set.Source
  $source = [System.Drawing.Bitmap]::FromFile($sourcePath)
  $setFolder = Join-Path $outputRoot $set.Slug
  New-Item -ItemType Directory -Force -Path $setFolder | Out-Null

  for ($row = 0; $row -lt $set.Rows; $row++) {
    for ($column = 0; $column -lt 4; $column++) {
      $left = [Math]::Floor($source.Width * $column / 4)
      $right = [Math]::Floor($source.Width * ($column + 1) / 4)
      $top = [Math]::Floor($source.Height * $row / $set.Rows)
      $bottom = [Math]::Floor($source.Height * ($row + 1) / $set.Rows)
      $crop = New-Object System.Drawing.Bitmap ($right - $left), ($bottom - $top), ([System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
      $graphics = [System.Drawing.Graphics]::FromImage($crop)
      $graphics.DrawImage($source, (New-Object System.Drawing.Rectangle 0, 0, $crop.Width, $crop.Height), (New-Object System.Drawing.Rectangle $left, $top, $crop.Width, $crop.Height), [System.Drawing.GraphicsUnit]::Pixel)
      $graphics.Dispose()

      if ($set.Slug -in @('red-soldier', 'red-torch')) { Remove-BlueBackground $crop }
      $tile = New-Object System.Drawing.Bitmap 256, 256, ([System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
      $tileGraphics = [System.Drawing.Graphics]::FromImage($tile)
      $tileGraphics.Clear([System.Drawing.Color]::Transparent)
      $scale = [Math]::Min(244 / $crop.Width, 244 / $crop.Height)
      $drawWidth = [Math]::Round($crop.Width * $scale)
      $drawHeight = [Math]::Round($crop.Height * $scale)
      $drawLeft = [Math]::Round((256 - $drawWidth) / 2)
      $drawTop = [Math]::Round((256 - $drawHeight) / 2)
      $tileGraphics.DrawImage($crop, (New-Object System.Drawing.Rectangle $drawLeft, $drawTop, $drawWidth, $drawHeight))
      $tileGraphics.Dispose()
      $target = Join-Path $setFolder ('{0:D2}.png' -f ($row * 4 + $column + 1))
      $tile.Save($target, [System.Drawing.Imaging.ImageFormat]::Png)
      $tile.Dispose()
      $crop.Dispose()
    }
  }
  $source.Dispose()
}
