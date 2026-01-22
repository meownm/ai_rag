@echo off
setlocal
title ai_rag infra deploy_docker_desktop

call "%~dp0install.bat"
if errorlevel 1 goto :err

call "%~dp0start.bat"
if errorlevel 1 goto :err

call "%~dp0smoke_test.bat"
if errorlevel 1 goto :err

exit /b 0

:err
echo [ERROR] deploy failed.
pause
exit /b 1
