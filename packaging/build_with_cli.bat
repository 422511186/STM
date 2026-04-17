@echo off
setlocal enabledelayedexpansion

echo.
echo ========================================
echo   STM Build Script (CLI Only)
echo ========================================
echo.

cd /d "%~dp0.."

if exist "config.yaml" (
    echo [CONFIG] config.yaml found.
) else (
    echo [WARN] config.yaml not found. Copy from config.yaml.example if needed.
)

python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo [INFO] PyInstaller not found. Installing...
    pip install pyinstaller
    if errorlevel 1 (
        echo [ERROR] Failed to install PyInstaller
        pause
        exit /b 1
    )
)

if exist "dist" (
    echo [CLEAN] Removing old dist folder...
    rmdir /s /q dist
)
if exist "build" (
    echo [CLEAN] Removing old build folder...
    rmdir /s /q build
)
if exist "*.spec" (
    echo [CLEAN] Removing old spec files...
    del /q *.spec >nul 2>&1
)

echo.
echo [BUILD] Building stm.exe, please wait...
echo.

python -m PyInstaller --onefile --name stm --console stm_cli.py

echo.
if exist "dist\stm.exe" (
    for %%A in ("dist\stm.exe") do set size=%%~zA
    set /a mb=!size!/1024/1024
    set /a kb=!size!/1024
    echo ========================================
    echo   Build succeeded!
    echo   Output: dist\stm.exe (!kb! KB / !mb! MB)
    echo ========================================
) else (
    if exist "build\stm\warn-stm.txt" (
        echo [WARN] Build completed with warnings. Check build\stm\warn-stm.txt
    ) else (
        echo [FAILED] stm.exe not generated. Check logs above.
    )
)

echo.
endlocal
pause
