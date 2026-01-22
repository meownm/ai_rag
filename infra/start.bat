@echo off
setlocal
title ai_rag infra start

call "%~dp0install_prereqs.bat"
if errorlevel 1 goto :err

if not exist "..\.env" (
  echo [ERROR] ..\.env not found. Run infra\install.bat first.
  goto :err
)

call "%~dp0_lib_env.bat" "%~dp0..\..\.env"
if errorlevel 1 goto :err

pushd "%~dp0docker"
if errorlevel 1 goto :err

docker compose --env-file "..\.env" up -d
if errorlevel 1 goto :err

docker compose --env-file "..\.env" run --rm db-migrator
if errorlevel 1 goto :err

docker compose --env-file "..\.env" run --rm minio-init
if errorlevel 1 goto :err

popd

echo.
echo [INFO] Infra is up.
echo.
echo [INFO] URLs:
echo   PostgreSQL:        localhost:%POSTGRES_HOST_PORT%  (db=%POSTGRES_DB%)
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
echo [ERROR] infra start failed.
popd
pause
exit /b 1
