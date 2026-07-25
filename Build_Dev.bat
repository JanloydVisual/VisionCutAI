@echo off
setlocal
title VisionCut AI - Automatic Development Build

REM Activate virtual environment
call venv\Scripts\activate.bat

echo Cleaning previous build...
rmdir /s /q dist 2>nul
rmdir /s /q build 2>nul

echo Building Development version with PyInstaller (--onedir)...
pyinstaller --windowed --onedir --name VisionCutAI ^
    --add-data "models;models" ^
    --add-data "assets;assets" ^
    --hidden-import "cv2" ^
    --hidden-import "numpy" ^
    --hidden-import "rembg" ^
    --hidden-import "onnxruntime" ^
    app.py

if not exist "dist\VisionCutAI\VisionCutAI.exe" (
    echo.
    echo ❌ Build Failed
    echo Desktop version was not modified.
    pause
    exit /b 1
)

echo.
echo ✔ Build Successful

REM Kill any running instances
taskkill /F /IM VisionCutAI.exe /T 2>nul
REM Give it a moment to close completely
ping 127.0.0.1 -n 3 >nul

REM Get the actual Desktop folder path (handling OneDrive/Redirection)
FOR /F "tokens=*" %%A IN ('powershell -command "[Environment]::GetFolderPath('Desktop')"') DO SET "DEST_BASE=%%A"
set "DEST=%DEST_BASE%\VisionCut AI Dev"

echo Deploying to Desktop...
rmdir /s /q "%DEST%" 2>nul
mkdir "%DEST%" 2>nul
xcopy "dist\VisionCutAI\*" "%DEST%\" /E /I /H /Y >nul

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ Deployment Failed
    pause
    exit /b 1
)

echo ✔ Desktop Updated

echo Launching application...
cd /d "%DEST%"
set VISIONCUT_ENV=development
start "" "VisionCutAI.exe"

echo ✔ Application Launched
echo.
pause
