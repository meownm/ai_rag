\
@echo off
setlocal
title rag-platform stop_all

call "%~dp0install_prereqs.bat"
if errorlevel 1 goto :err

pushd "%~dp0docker"
if errorlevel 1 goto :err

docker compose --profile app down --remove-orphans
if errorlevel 1 goto :err

popd
exit /b 0

:err
echo [ERROR] stop_all failed.
popd
pause
exit /b 1
