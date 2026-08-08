@echo off
chcp 65001 >nul 2>&1
echo ============================================
echo   LinguaAI - AI-Powered Learning App
echo ============================================
echo.
echo Katalog: %~dp0
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
start "LinguaAI-Backend" cmd /k "cd /d %~dp0 && py -3.11 -m uvicorn backend.main:app --reload --port 8001"

echo [2/2] Uruchamianie frontendu...
REM Uwaga: npm install TYLKO gdy brak node_modules, ale npm run dev URUCHAM ZAWSZE.
REM (Uzycie "&" zamiast "&&" — inaczej gdy node_modules istnieje, if jest falszywy
REM  i cala reszta linii z npm run dev zostaje pominieta -> frontend nigdy nie wstaje.)
start "LinguaAI-Frontend" cmd /k "cd /d %~dp0frontend && (if not exist node_modules npm install) & npm run dev"

echo.
echo ============================================
echo   Backend:  http://localhost:8001
echo   Frontend: http://localhost:5173
echo ============================================
echo.
echo Czekam na uruchomienie serwerow...
timeout /t 5 /nobreak >nul
echo Sprawdzam czy frontend jest gotowy...
set /a tries=0
:check_frontend
curl -s -f http://localhost:5173 >nul 2>&1
if not errorlevel 1 goto frontend_ready
set /a tries+=1
if %tries% geq 40 (
    echo.
    echo [BLAD] Frontend nie wstal po ~120s.
    echo Sprawdz okno "LinguaAI-Frontend" — powinien tam byc log vite lub blad.
    echo.
    pause
    exit /b 1
)
echo Frontend jeszcze sie kompiluje, czekam... (%tries%/40)
timeout /t 3 /nobreak >nul
goto check_frontend

:frontend_ready
echo Frontend gotowy! Otwieram przegladarke...
start http://localhost:5173
