# RailTwin-X 1-Click Signature Hackathon Demo Launcher (SIH PS 26028)
# Boots API server on port 8000, Web app on port 5173, and launches browser to Live Comparator.

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "  RailTwin-X: Dynamic ETA Forecast & Station OS (SIH PS 26028)  " -ForegroundColor Yellow
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "[1/4] Checking python environment and database..." -ForegroundColor Green

Set-Location $RepoRoot
python -c "from data.db import get_db; db = get_db(); db.init_schema(); print(f'Database verified: {db.table_counts()}')"

Write-Host "[2/4] Starting FastAPI backend on http://localhost:8000..." -ForegroundColor Green
$BackendProcess = Start-Process -FilePath "python" -ArgumentList "-m uvicorn api.main:app --host 0.0.0.0 --port 8000" -PassThru -NoNewWindow

Write-Host "[3/4] Starting Vite web dashboard on http://localhost:5173..." -ForegroundColor Green
Set-Location "$RepoRoot\web"
$FrontendProcess = Start-Process -FilePath "cmd.exe" -ArgumentList "/c npm run dev" -PassThru -NoNewWindow

Start-Sleep -Seconds 4

Write-Host "[4/4] Launching browser to Signature Demo Comparator..." -ForegroundColor Yellow
Start-Process "http://localhost:5173/compare"

Write-Host ""
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "  DEMO READY! Press Ctrl+C or close window to stop services.     " -ForegroundColor Green
Write-Host "  Foresight Console : http://localhost:5173/                     " -ForegroundColor White
Write-Host "  Live Comparator   : http://localhost:5173/compare              " -ForegroundColor White
Write-Host "  The Time Machine  : http://localhost:5173/replay               " -ForegroundColor White
Write-Host "  Ripple Board & DSS: http://localhost:5173/cascade              " -ForegroundColor White
Write-Host "  Honest Model Card : http://localhost:5173/model-card           " -ForegroundColor White
Write-Host "=================================================================" -ForegroundColor Cyan

Wait-Process -Id $BackendProcess.Id
