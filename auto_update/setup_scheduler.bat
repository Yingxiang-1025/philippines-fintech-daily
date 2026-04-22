@echo off
REM ─────────────────────────────────────────────────────
REM  Philippines Fintech Daily Brief - Windows Task Scheduler Setup
REM  Run as Administrator to create a daily scheduled task
REM ─────────────────────────────────────────────────────

set TASK_NAME=PhilippinesFintechDailyBrief
set SCRIPT_DIR=%~dp0
set PYTHON_PATH=python

echo.
echo ===================================================
echo  Setting up daily scheduled task: %TASK_NAME%
echo  Script: %SCRIPT_DIR%main.py
echo  Schedule: Daily at 08:00
echo ===================================================
echo.

REM Delete existing task if any
schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1

REM Create new scheduled task
schtasks /create ^
    /tn "%TASK_NAME%" ^
    /tr "\"%PYTHON_PATH%\" \"%SCRIPT_DIR%main.py\"" ^
    /sc daily ^
    /st 08:00 ^
    /rl HIGHEST ^
    /f

if %errorlevel% equ 0 (
    echo.
    echo [OK] Task created successfully!
    echo     Name: %TASK_NAME%
    echo     Schedule: Daily at 08:00
    echo     Script: %SCRIPT_DIR%main.py
    echo.
    echo To modify: Open Task Scheduler and find "%TASK_NAME%"
    echo To delete: schtasks /delete /tn "%TASK_NAME%" /f
) else (
    echo.
    echo [ERROR] Failed to create task. Try running as Administrator.
)

pause
