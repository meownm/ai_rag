\
@echo off
setlocal
title rag-platform smoke_test

call "%~dp0install_prereqs.bat"
if errorlevel 1 goto :err

call "%~dp0_lib_env.bat" "%~dp0..\..\.env"
if errorlevel 1 goto :err

set "PG_CONT=%PROJECT_NAME%-postgres"

docker ps --format "{{.Names}}" | findstr /i /x "%PG_CONT%" >nul
if errorlevel 1 goto :err

docker exec "%PG_CONT%" psql -U "%POSTGRES_SUPERUSER%" -d "%POSTGRES_DB%" -tAc "SELECT count(*) FROM public.schema_migrations;" >nul 2>&1
if errorlevel 1 goto :err

curl -fsS "http://localhost:%GATEWAY_API_HOST_PORT%/health" >nul 2>&1
if errorlevel 1 goto :err

curl -fsS "http://localhost:%GATEWAY_API_HOST_PORT%%METRICS_PATH%" >nul 2>&1
if errorlevel 1 goto :err

echo [INFO] Smoke test PASSED.
exit /b 0

:err
echo [ERROR] Smoke test FAILED.
pause
exit /b 1
