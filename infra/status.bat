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

title ai_rag status

call "%~dp0install_prereqs.bat"
if errorlevel 1 goto :err

call "%~dp0_lib_env.bat" "%ENV_FILE%"
if errorlevel 1 goto :err

echo [INFO] Project: %PROJECT_NAME%
docker ps --format "table {{.Names}}	{{.Status}}	{{.Ports}}" | findstr /i "%PROJECT_NAME%"

echo.
echo [INFO] URLs:
echo   Grafana:    http://localhost:%GRAFANA_HOST_PORT%
echo   Prometheus: http://localhost:%PROMETHEUS_HOST_PORT%
echo   Loki:       http://localhost:%LOKI_HOST_PORT%
echo   pgAdmin:    http://localhost:%PGADMIN_HOST_PORT%
echo   Adminer:    http://localhost:%ADMINER_HOST_PORT%
echo   pgHero:     http://localhost:%PGHERO_HOST_PORT%
echo   MinIO:      http://localhost:%MINIO_API_HOST_PORT%
echo   MinIO UI:   http://localhost:%MINIO_CONSOLE_HOST_PORT%
endlocal
exit /b 0

:err
echo [ERROR] status failed.
pause
endlocal
exit /b 1
