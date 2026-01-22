\
@echo off
setlocal
title rag-platform deploy_docker_desktop

call "%~dp0install.bat"
if errorlevel 1 goto :err

call "%~dp0start_all.bat"
if errorlevel 1 goto :err

exit /b 0

:err
echo [ERROR] deploy failed.
pause
exit /b 1
