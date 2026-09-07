@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_app.ps1" %*
if errorlevel 1 (
    echo.
    echo Startup failed. Please keep this message and check the .runtime logs.
    pause
)
