@echo off
title Dictation App
color 0B

:: Change to the folder where this bat file lives so the script path is always correct
cd /d "%~dp0"

echo ============================================================
echo   Free Dictation App
echo   Hold RIGHT ALT anywhere on Windows to dictate.
echo   Release to transcribe and type.
echo   Close this window to quit.
echo ============================================================
echo.

:: Check Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in your PATH.
    echo Download Python from https://www.python.org
    pause
    exit /b 1
)

:: Run the app using the new Sovereign Web Engine
python main.py

echo.
echo App closed.
pause
