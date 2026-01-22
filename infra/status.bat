@echo off
setlocal
title ai_rag infra status

call "%~dp0install_prereqs.bat"
if errorlevel 1 goto :err

call "%~dp0_lib_env.bat" "%~dp0..\..\.env"
if errorlevel 1 goto :err

echo [INFO] Project: %PROJECT_NAME%
echo.

docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | findstr /i "%PROJECT_NAME%"

echo.
echo [INFO] URLs:
echo   pgAdmin:          http://localhost:%PGADMIN_HOST_PORT%
echo   Adminer:          http://localhost:%ADMINER_HOST_PORT%
echo   pgHero:           http://localhost:%PGHERO_HOST_PORT%
echo   Grafana:          http://localhost:%GRAFANA_HOST_PORT%
echo   Prometheus:       http://localhost:%PROMETHEUS_HOST_PORT%
echo   Loki:             http://localhost:%LOKI_HOST_PORT%
echo   MinIO Console:    http://localhost:%MINIO_CONSOLE_HOST_PORT%
echo   MinIO API:        http://localhost:%MINIO_API_HOST_PORT%
echo.
exit /b 0

:err
echo [ERROR] status failed.
pause
exit /b 1
