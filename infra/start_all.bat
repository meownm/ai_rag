\
@echo off
setlocal
title rag-platform start_all

call "%~dp0install_prereqs.bat"
if errorlevel 1 goto :err

call "%~dp0start.bat"
if errorlevel 1 goto :err

pushd "%~dp0docker"
if errorlevel 1 goto :err

docker compose --env-file "..\.env" --profile app up -d --build
if errorlevel 1 goto :err

popd

call "%~dp0smoke_test.bat"
if errorlevel 1 goto :err

exit /b 0

:err
echo [ERROR] start_all failed.
pause
exit /b 1
