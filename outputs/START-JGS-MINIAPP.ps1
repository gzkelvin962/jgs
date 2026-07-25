$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

$envFile = Join-Path $PSScriptRoot ".env.local"
if (-not $env:OPENAI_API_KEY -and -not (Test-Path -LiteralPath $envFile)) {
  Write-Host "首次启动需要管理员配置 OpenAI API Key。" -ForegroundColor Yellow
  Write-Host "1. 复制 .env.local.example 为 .env.local"
  Write-Host "2. 在 .env.local 中填写 OPENAI_API_KEY"
  Write-Host "3. 再次运行本脚本。普通用户不需要填写任何地址或密钥。"
  exit 2
}

$python = Get-Command python -ErrorAction SilentlyContinue
if ($python) {
  Write-Host "小程序地址：http://127.0.0.1:8787/" -ForegroundColor Green
  & $python.Source ".\jinggangshan-agent-api-example.py"
  exit $LASTEXITCODE
}

$py = Get-Command py -ErrorAction SilentlyContinue
if ($py) {
  Write-Host "小程序地址：http://127.0.0.1:8787/" -ForegroundColor Green
  & $py.Source -3 ".\jinggangshan-agent-api-example.py"
  exit $LASTEXITCODE
}

Write-Host "未找到 Python 3，请先安装 Python 3.10 或更高版本。" -ForegroundColor Red
exit 3
