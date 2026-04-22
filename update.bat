@echo off
chcp 65001 >nul
echo ============================================
echo   Philippines Fintech Daily Brief - Update
echo ============================================
echo.

cd /d "%~dp0auto_update"

echo [%date% %time%] Starting daily update...
python main.py

if %errorlevel% equ 0 (
    echo.
    echo [OK] Update completed successfully!
) else (
    echo.
    echo [ERROR] Update failed with error code %errorlevel%
)

echo.
echo Press any key to exit...
pause >nul
