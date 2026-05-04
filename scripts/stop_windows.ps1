$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir

Set-Location $ProjectDir

Write-Host "Stopping FinAlly..."
docker compose down

Write-Host "FinAlly stopped. Data is preserved in the Docker volume."
Write-Host "To remove data: docker volume rm finally_finally-data"
