@echo off
chcp 65001 >nul
echo ============================================
echo   Philippines Fintech Daily Brief - Server
echo ============================================
echo.
echo Starting local web server at http://localhost:8080
echo Press Ctrl+C to stop.
echo.

cd /d "%~dp0"
python -m http.server 8080

pause
