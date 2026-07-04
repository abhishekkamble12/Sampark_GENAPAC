@echo off
title Sampark AI Platform - Demo Launcher
echo =======================================================================
echo               SAMPARK AI PLATFORM - DEMO LAUNCHER
echo =======================================================================
echo.

echo [1/3] Verifying and installing Python backend dependencies...
pip install -e ".[dev]"
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python dependency installation failed!
    pause
    exit /b %ERRORLEVEL%
)
echo.

echo [2/3] Verifying and installing React frontend dependencies...
cd frontend
call npm install
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Frontend npm install failed!
    cd ..
    pause
    exit /b %ERRORLEVEL%
)
cd ..
echo.

echo [3/3] Launching local servers...
echo.

echo - Starting FastAPI backend on port 8000...
start "Sampark Backend Gateway" cmd /c "uvicorn backend.main:app --reload --port 8000"

echo - Starting Vite frontend on port 5173...
start "Sampark Frontend Client" cmd /c "cd frontend && npm run dev"

echo.
echo Waiting for servers to initialize...
timeout /t 3 /nobreak >nul

echo Opening browser to http://localhost:5173 ...
start http://localhost:5173

echo.
echo =======================================================================
echo Sampark AI Demo is now running!
echo Backend: http://localhost:8000
echo Frontend: http://localhost:5173
echo.
echo Press any key in this window to stop and close the server windows...
echo =======================================================================
pause >nul

echo Stopping servers...
taskkill /FI "WINDOWTITLE eq Sampark Backend Gateway*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Sampark Frontend Client*" /T /F >nul 2>&1
echo Done!
