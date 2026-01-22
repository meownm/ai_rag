\
@echo off
setlocal
title rag-platform infra start

call "%~dp0install_prereqs.bat"
if errorlevel 1 goto :err

if not exist "..\.env" (
  echo [ERROR] ..\.env not found. Run infra\install.bat first.
  goto :err
)

pushd "%~dp0docker"
if errorlevel 1 goto :err

docker compose --env-file "..\.env" up -d
if errorlevel 1 goto :err

docker compose --env-file "..\.env" run --rm db-migrator
if errorlevel 1 goto :err

docker compose --env-file "..\.env" run --rm minio-init
if errorlevel 1 goto :err

popd
exit /b 0

:err
echo [ERROR] infra start failed.
popd
pause
exit /b 1
