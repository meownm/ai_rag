@echo off
setlocal
set "ROOT_DIR=%~dp0.."
set "ENV_FILE=%ROOT_DIR%\.env"
set "ENV_EXAMPLE_ROOT=%ROOT_DIR%\.env.example"
set "ENV_EXAMPLE_INFRA=%~dp0\.env.example"

if not exist "%ENV_FILE%" (
  if exist "%ENV_EXAMPLE_ROOT%" (
    copy "%ENV_EXAMPLE_ROOT%" "%ENV_FILE%" >nul
    echo [INFO] Created %ENV_FILE% from %ENV_EXAMPLE_ROOT%
  ) else if exist "%ENV_EXAMPLE_INFRA%" (
    copy "%ENV_EXAMPLE_INFRA%" "%ENV_FILE%" >nul
    echo [INFO] Created %ENV_FILE% from %ENV_EXAMPLE_INFRA%
  ) else (
    echo [ERROR] .env.example not found in root or infra.
    endlocal
    exit /b 1
  )
) else (
  rem .env already exists
)

title ai_rag smoke_test

call "%~dp0install_prereqs.bat"
if errorlevel 1 goto :err

call "%~dp0_lib_env.bat" "%ENV_FILE%"
if errorlevel 1 goto :err

set "PG_CONT=%PROJECT_NAME%-postgres"

docker ps --format "{{.Names}}" | findstr /i /x "%PG_CONT%" >nul
if errorlevel 1 (
  echo [ERROR] Postgres container not running: %PG_CONT%
  goto :err
)

docker exec "%PG_CONT%" psql -U "%POSTGRES_SUPERUSER%" -d "%POSTGRES_DB%" -tAc "SELECT 1 FROM public.schema_migrations LIMIT 1;" >nul 2>&1
if errorlevel 1 (
  echo [ERROR] DB migrations not applied (schema_migrations check failed)
  goto :err
)

docker exec "%PG_CONT%" psql -U "%POSTGRES_SUPERUSER%" -d "%POSTGRES_DB%" -tAc "SELECT 1 FROM app.documents LIMIT 1;" >nul 2>&1
if errorlevel 1 (
  echo [ERROR] app.documents not accessible
  goto :err
)

curl -fsS "http://localhost:%MINIO_API_HOST_PORT%/minio/health/ready" >nul 2>&1
if errorlevel 1 (
  echo [ERROR] MinIO readiness failed
  goto :err
)

curl -fsS "http://localhost:%PROMETHEUS_HOST_PORT%/-/ready" >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Prometheus readiness failed
  goto :err
)

curl -fsS "http://localhost:%GRAFANA_HOST_PORT%/api/health" >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Grafana health failed
  goto :err
)

echo [INFO] Smoke test PASSED.
endlocal
exit /b 0

:err
echo [ERROR] Smoke test FAILED.
pause
endlocal
exit /b 1
