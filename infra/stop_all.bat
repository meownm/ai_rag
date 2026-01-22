@echo off
setlocal
title ai_rag infra stop

call "%~dp0install_prereqs.bat"
if errorlevel 1 goto :err

pushd "%~dp0docker"
if errorlevel 1 goto :err

docker compose down --remove-orphans
if errorlevel 1 goto :err

popd
exit /b 0

:err
echo [ERROR] infra stop failed.
popd
pause
exit /b 1
