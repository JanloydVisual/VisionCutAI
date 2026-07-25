@echo off
title VisionCut AI - Release Build
echo ========================================
echo VisionCut AI Release Build Script
echo ========================================
echo.

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Clean previous build
echo Cleaning previous build...
rmdir /s /q dist 2>nul
rmdir /s /q build 2>nul
del /q VisionCutAI.spec 2>nul

REM Build with PyInstaller
echo Building with PyInstaller...
pyinstaller --windowed --onefile --name VisionCutAI ^
    --clean ^
    --add-data "models;models" ^
    --add-data "assets;assets" ^
    --hidden-import "cv2" ^
    --hidden-import "numpy" ^
    --hidden-import "rembg" ^
    --hidden-import "onnxruntime" ^
    app.py

REM Check if build succeeded
if exist "dist\VisionCutAI.exe" (
    echo.
    echo Build successful! Executable created at: dist\VisionCutAI.exe
    
    REM Create release folder
    echo Creating release folder...
    mkdir "VisionCutAI" 2>nul
    copy "dist\VisionCutAI.exe" "VisionCutAI\" >nul
    
    REM Create model and asset folders in release
    mkdir "VisionCutAI\models" 2>nul
    mkdir "VisionCutAI\assets" 2>nul
    
    REM Copy model files if they exist
    if exist "models\*" (
        xcopy "models\*" "VisionCutAI\models\" /E /I /Y >nul
    )
    
    REM Copy asset files if they exist
    if exist "assets\*" (
        xcopy "assets\*" "VisionCutAI\assets\" /E /I /Y >nul
    )
    
    echo Release folder created: VisionCutAI\
) else (
    echo.
    echo Build failed! Check the error messages above.
)

echo.
pause