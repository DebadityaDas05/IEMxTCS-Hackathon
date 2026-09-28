@echo off
chcp 65001 >nul
title Intelligent Enterprise Knowledge Assistant - Launcher
setlocal enabledelayedexpansion

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

echo ======================================================================
echo    🧠 Intelligent Enterprise Knowledge Assistant
echo    RAG-Based Document Q^&A System
echo ======================================================================
echo.

:: 1. Check Python
echo [1/4] Checking Python environment...
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not found in your PATH!
    echo Please install Python 3.10+ and make sure it is added to your PATH.
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do set "PY_VER=%%v"
echo    ✓ Found %PY_VER%

:: 2. Check Node.js and npm
echo [2/4] Checking Node.js environment...
where npm >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] npm is not found in your PATH!
    echo Please install Node.js 18+ from https://nodejs.org/
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('node --version 2^>^&1') do set "NODE_VER=%%v"
echo    ✓ Found Node.js %NODE_VER%

:: 3. Check and ensure Ollama is active
echo [3/4] Checking Ollama service...
where ollama >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo    ⚠️  Ollama executable not found in PATH.
    echo       Make sure Ollama is installed and running at http://localhost:11434
) else (
    curl.exe -s http://localhost:11434/api/tags >nul 2>&1
    if !ERRORLEVEL! equ 0 (
        echo    ✓ Ollama is online and responding.
    ) else (
        echo    Starting Ollama service in background...
        start "Ollama Service" /min cmd /c "ollama serve"
        timeout /t 3 /nobreak >nul
        echo    ✓ Ollama service launched.
    )
)

:: Ensure frontend dependencies are installed
if not exist "%ROOT_DIR%frontend\node_modules" (
    echo.
    echo [Setup] Installing frontend dependencies (npm install)...
    cd /d "%ROOT_DIR%frontend"
    call npm install
    cd /d "%ROOT_DIR%"
)

echo.
echo [4/4] Launching Backend and Frontend services...
echo.

:: Launch FastAPI Backend in a separate window
echo    Launching FastAPI Backend (Port 8000)...
start "🧠 Knowledge Assistant - Backend (Port 8000)" cmd /k "chcp 65001 >nul && cd /d "%ROOT_DIR%backend" && set PYTHONUTF8=1 && set PYTHONIOENCODING=utf-8 && echo ========================================== && echo  FastAPI Backend Server - Port 8000 && echo  API Docs: http://localhost:8000/docs && echo ========================================== && echo. && python -m uvicorn app.main:app --reload --port 8000"

:: Launch React/Vite Frontend in a separate window
echo    Launching React Frontend (Port 5173)...
start "💻 Knowledge Assistant - Frontend (Port 5173)" cmd /k "cd /d "%ROOT_DIR%frontend" && echo ========================================== && echo  Vite Dev Server - Port 5173 && echo  URL: http://localhost:5173 && echo ========================================== && echo. && npm run dev"

:: Wait a brief moment for dev servers to bind ports
echo.
echo Waiting 4 seconds for servers to initialize...
timeout /t 4 /nobreak >nul

:: Open browser
echo Opening Web Application in your default browser...
start http://localhost:5173

echo.
echo ======================================================================
echo    🎉 Enterprise Knowledge Assistant is RUNNING!
echo ======================================================================
echo    - Frontend UI:  http://localhost:5173
echo    - Backend API:  http://localhost:8000
echo    - Swagger Docs: http://localhost:8000/docs
echo    - Ollama API:   http://localhost:11434
echo ======================================================================
echo.
echo  The Backend and Frontend are running in their respective console windows.
echo  To shut down both servers, run stop.bat or close their terminal windows.
echo.
pause
