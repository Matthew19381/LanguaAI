# LinguaAI - PowerShell Launcher
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  LinguaAI - AI-Powered Learning App" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Check if .env exists (root or backend/)
$envRoot = Test-Path ".env"
$envBackend = Test-Path "backend\.env"
if (-not $envRoot -and -not $envBackend) {
    Write-Host "[WARNING] .env not found!" -ForegroundColor Yellow
    Write-Host "Please copy .env.example to .env and add your API keys."
    Write-Host ""
    Read-Host "Press Enter to continue anyway..."
} elseif ($envRoot) {
    Write-Host "Found .env at project root." -ForegroundColor Green
} else {
    Write-Host "Found .env in backend/." -ForegroundColor Green
}

$rootDir = $PWD.Path

Write-Host "Starting LinguaAI Backend..." -ForegroundColor Green
$backendCmd = "Set-Location '$rootDir'; Write-Host 'Starting backend on http://localhost:8001' -ForegroundColor Green; py -3.11 -m pip install -r backend
equirements.txt; py -3.11 -m uvicorn backend.main:app --reload --port 8001"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd

Start-Sleep -Seconds 3

Write-Host "Starting LinguaAI Frontend..." -ForegroundColor Green
$frontendCmd = "Set-Location '$rootDir\frontend'; Write-Host 'Starting frontend on http://localhost:5173' -ForegroundColor Green; npm install; npm run dev"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Services starting up..." -ForegroundColor Green
Write-Host "  Backend:  http://localhost:8001" -ForegroundColor White
Write-Host "  Frontend: http://localhost:5173" -ForegroundColor White
Write-Host "  API Docs: http://localhost:8001/docs" -ForegroundColor White
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Waiting for frontend to compile..." -ForegroundColor Yellow

# Wait for frontend to be ready
$maxRetries = 30
$retryCount = 0
while ($retryCount -lt $maxRetries) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:5173" -Method Get -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host "Frontend ready! Opening browser..." -ForegroundColor Green
            Start-Process "http://localhost:5173"
            break
        }
    } catch {
        # Frontend not ready yet
    }
    $retryCount++
    Write-Host "Frontend still compiling... ($retryCount/$maxRetries)" -ForegroundColor Yellow
    Start-Sleep -Seconds 3
}

if ($retryCount -ge $maxRetries) {
    Write-Host "Timeout waiting for frontend. Please open http://localhost:5173 manually." -ForegroundColor Red
}

Write-Host ""
Read-Host "Press Enter to exit this window"
