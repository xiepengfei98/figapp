@echo off
title FigApp - Script Hub
chcp 65001 >nul

echo ==========================================
echo   FigApp - Interactive Visualization Hub
echo ==========================================
echo.

if not exist venv\Scripts\python.exe (
    echo [ERROR] Virtual environment not found. Run setup.bat first.
    pause
    exit /b 1
)

REM AI features are optional. Set keys via environment variables, never hardcode.
REM Example: set DEEPSEEK_API_KEY=your_key  and  set MINIMAX_API_KEY=your_key
REM Or add them permanently in Windows System Environment Variables.
if "%DEEPSEEK_API_KEY%"=="" echo [INFO] DEEPSEEK_API_KEY not set - AI script assistant disabled.
if "%MINIMAX_API_KEY%"=="" echo [INFO] MINIMAX_API_KEY not set - image analysis disabled.

REM Ensure required directories exist
if not exist uploads mkdir uploads
if not exist outputs mkdir outputs
if not exist thumbnails mkdir thumbnails
if not exist scripts\R mkdir scripts\R
if not exist scripts\python mkdir scripts\python
if not exist scripts\data_process mkdir scripts\data_process

venv\Scripts\python.exe app.py

pause
