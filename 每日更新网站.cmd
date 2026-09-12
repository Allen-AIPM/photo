@echo off
chcp 65001 >nul
cd /d "%~dp0"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0automation\daily_update.ps1"
if errorlevel 1 (
  echo.
  echo Update failed. See update-log.txt for details.
  pause
  exit /b 1
)
