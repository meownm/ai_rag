\
@echo off
setlocal
title rag-platform reset_all

call "%~dp0install_prereqs.bat"
if errorlevel 1 goto :err

pushd "%~dp0docker"
if errorlevel 1 goto :err

echo [WARN] Removing containers and volumes for this project.
echo [WARN] No confirmation mode enabled (reset-no-confirm).

docker compose --profile app down -v --remove-orphans
if errorlevel 1 goto :err

popd
exit /b 0

:err
echo [ERROR] reset_all failed.
popd
pause
exit /b 1
