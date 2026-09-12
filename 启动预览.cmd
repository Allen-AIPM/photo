@echo off
cd /d "%~dp0"
if not exist node_modules call npm ci
if errorlevel 1 goto failed
call npm run dev -- --open
goto end
:failed
echo Dependency installation failed. Please check Node.js and your network.
:end
pause
