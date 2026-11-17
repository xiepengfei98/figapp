@echo off
title FigApp - Setup
chcp 65001 >nul

echo ==========================================
echo   FigApp - First-time Setup
echo ==========================================
echo.

echo [1/3] Checking Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Install Python 3.9+ from https://www.python.org/downloads/
    pause
    exit /b 1
)
python --version
echo.

echo [2/3] Creating virtual environment...
if exist venv\ (
    echo Virtual environment already exists, skipping.
) else (
    python -m venv venv
    echo Virtual environment created.
)
echo.

echo [3/3] Installing dependencies...
venv\Scripts\python.exe -m pip install --upgrade pip --quiet
venv\Scripts\python.exe -m pip install -r requirements.txt --quiet
echo Dependencies installed.
echo.

echo Checking R ^(optional, only needed for R scripts^)...
where Rscript >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Rscript not found. R scripts will be unavailable.
    echo Install R from https://cran.r-project.org/
) else (
    Rscript --version
)
echo.

echo ==========================================
echo   Setup complete. Run start.bat to launch.
echo ==========================================
pause
