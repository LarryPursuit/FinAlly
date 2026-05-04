$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir

Set-Location $ProjectDir

# Check for .env file
if (-not (Test-Path ".env")) {
    Write-Host "Warning: .env file not found. Copying from .env.example..."
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "Created .env from .env.example. Edit it to add your API keys."
    } else {
        Write-Error "Neither .env nor .env.example found."
        exit 1
    }
}

Write-Host "Building and starting FinAlly..."
docker compose up --build -d

Write-Host ""
Write-Host "FinAlly is running at: http://localhost:8000"
Write-Host "To stop: .\scripts\stop_windows.ps1"

# Open browser
Start-Sleep -Seconds 2
Start-Process "http://localhost:8000"
