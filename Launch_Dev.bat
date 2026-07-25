@echo off
title VisionCut AI - Development Mode
echo ========================================
echo VisionCut AI Development Launcher
echo ========================================
echo.

set VISIONCUT_ENV=development
set PYTHONPATH=%~dp0

if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo [WARNING] venv not found. Ensure dependencies are installed!
)

echo Launching application...
python app.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Application exited with code %ERRORLEVEL%
    pause
)
