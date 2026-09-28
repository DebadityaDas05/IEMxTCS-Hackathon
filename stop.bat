@echo off
chcp 65001 >nul
title Intelligent Enterprise Knowledge Assistant - Stopper
setlocal enabledelayedexpansion

echo ======================================================================
echo    🛑 Stopping Intelligent Enterprise Knowledge Assistant...
echo ======================================================================
echo.

:: Kill process listening on port 8000 (Backend / uvicorn)
echo [1/2] Stopping Backend on port 8000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
    echo    ✓ Stopped process with PID %%a
)

:: Kill process listening on port 5173 (Frontend / Vite)
echo [2/2] Stopping Frontend on port 5173...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5173 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
    echo    ✓ Stopped process with PID %%a
)

echo.
echo ======================================================================
echo    ✅ Services stopped successfully.
echo ======================================================================
echo.
pause
