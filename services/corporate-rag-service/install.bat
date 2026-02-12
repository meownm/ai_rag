@echo off
setlocal EnableExtensions

poetry install
if errorlevel 1 goto :error

echo [OK] Dependencies installed.
exit /b 0

:error
echo [ERROR] install.bat failed.
pause
exit /b 1
