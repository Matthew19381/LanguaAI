@echo off
chcp 65001 >nul 2>&1
echo ============================================
echo   LinguaAI - AI-Powered Learning App
echo ============================================
echo.

REM Check if .env exists
if not exist "backend\.env" (
    if exist "backend\.env.example" (
        echo [UWAGA] backend\.env nie znaleziony!
        echo Kopiowanie .env.example do .env...
        copy backend\.env.example backend\.env
        echo Otworz backend\.env i ustaw OPENROUTER_API_KEY.
        pause
        exit /b 1
    )
)

echo [1/2] Uruchamianie backendu...
start "LinguaAI-Backend" cmd /k "cd /d %~dp0 && python -m uvicorn backend.main:app --reload --port 8001"

echo [2/2] Uruchamianie frontendu...
start "LinguaAI-Frontend" cmd /k "cd /d %~dp0\frontend && if not exist node_modules (npm install) && npm run dev"

echo.
echo ============================================
echo   Backend:  http://localhost:8001
echo   Frontend: http://localhost:5173
echo ============================================
echo.
echo Czekam na uruchomienie serwerow...
timeout /t 15 /nobreak >nul
echo Sprawdzam czy frontend jest gotowy...
:check_frontend
powershell -Command "try { $r = Invoke-WebRequest -Uri 'http://localhost:5173' -TimeoutSec 5; exit 0 } catch { exit 1 }" >nul 2>&1
if errorlevel 1 (
    echo Frontend jeszcze sie kompiluje, czekam...
    timeout /t 3 /nobreak >nul
    goto check_frontend
)
echo Frontend gotowy! Otwieram przegladarke...
start http://localhost:5173
