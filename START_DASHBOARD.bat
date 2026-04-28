@echo off
title CCAF Intelligence Dashboard
color 0A

echo.
echo  ============================================================
echo   CCAF INTELLIGENCE DASHBOARD
echo   Claude + Exam Updates - Last 7 Days
echo  ============================================================
echo.

set PYTHON=
for %%P in (python python3 py) do (
    if not defined PYTHON (
        %%P --version >nul 2>&1 && set PYTHON=%%P
    )
)

if not defined PYTHON (
    echo  [ERROR] Python not found. Please install Python 3.8+ from python.org
    pause
    exit /b 1
)

echo  [OK] Python found: %PYTHON%

echo  [..] Checking dependencies...
%PYTHON% -c "import requests, feedparser, bs4" >nul 2>&1
if errorlevel 1 (
    echo  [..] Installing required packages...
    %PYTHON% -m pip install requests feedparser beautifulsoup4 -q
    echo  [OK] Packages installed.
) else (
    echo  [OK] All dependencies present.
)

netstat -ano | findstr ":7474" >nul 2>&1
if not errorlevel 1 (
    echo  [..] Port 7474 in use - freeing it...
    for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":7474"') do (
        taskkill /PID %%a /F >nul 2>&1
    )
    timeout /t 1 >nul
)

echo.
echo  [..] Starting dashboard at http://localhost:7474
echo  Dashboard will open in your browser automatically.
echo  Press Ctrl+C in this window to stop the server.
echo  ============================================================
echo.

cd /d "%~dp0"
%PYTHON% server.py

echo.
echo  Server stopped. Press any key to exit.
pause >nul
