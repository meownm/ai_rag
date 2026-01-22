@echo off
setlocal
title ai_rag infra smoke_test

call "%~dp0install_prereqs.bat"
if errorlevel 1 goto :err

call "%~dp0_lib_env.bat" "%~dp0..\..\.env"
if errorlevel 1 goto :err

set "PG_CONT=%PROJECT_NAME%-postgres"
set "MINIO_URL=http://localhost:%MINIO_API_HOST_PORT%/minio/health/ready"
set "PROM_URL=http://localhost:%PROMETHEUS_HOST_PORT%/-/ready"
set "GRAF_URL=http://localhost:%GRAFANA_HOST_PORT%/api/health"

docker ps --format "{{.Names}}" | findstr /i /x "%PG_CONT%" >nul
if errorlevel 1 goto :err

docker exec "%PG_CONT%" psql -U "%POSTGRES_SUPERUSER%" -d "%POSTGRES_DB%" -tAc "SELECT count(*) FROM public.schema_migrations;" >nul 2>&1
if errorlevel 1 goto :err

docker exec "%PG_CONT%" psql -U "%POSTGRES_SUPERUSER%" -d "%POSTGRES_DB%" -tAc "SELECT to_regclass('app.documents') IS NOT NULL;" | findstr /i "t" >nul
if errorlevel 1 goto :err

curl -fsS "%MINIO_URL%" >nul 2>&1
if errorlevel 1 goto :err

curl -fsS "%PROM_URL%" >nul 2>&1
if errorlevel 1 goto :err

curl -fsS "%GRAF_URL%" >nul 2>&1
if errorlevel 1 goto :err

echo [INFO] Smoke test PASSED.
exit /b 0

:err
echo [ERROR] Smoke test FAILED.
pause
exit /b 1
