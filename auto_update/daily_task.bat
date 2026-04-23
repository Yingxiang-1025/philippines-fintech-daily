@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo [%date% %time%] Starting daily update... >> "%~dp0data\update.log"
python main.py >> "%~dp0data\update.log" 2>&1

echo [%date% %time%] Pushing to GitHub... >> "%~dp0data\update.log"
cd /d "%~dp0.."
git add -A >> "%~dp0data\update.log" 2>&1
git commit -m "Daily update %date%" >> "%~dp0data\update.log" 2>&1
git push >> "%~dp0data\update.log" 2>&1
echo [%date% %time%] Done. >> "%~dp0data\update.log"
