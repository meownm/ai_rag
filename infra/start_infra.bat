@echo off
setlocal enabledelayedexpansion
title rag-infra-start

if not exist ".env" (
  echo .env not found. Run install_infra.bat first.
  echo For continuation press any key.
  pause >nul
  exit /b 1
)

echo Starting infrastructure...
docker compose --env-file .env -f docker-compose.yml up -d
if errorlevel 1 (
  echo Failed to start infrastructure.
  echo For continuation press any key.
  pause >nul
  exit /b 1
)

echo.
echo Started.
echo PostgreSQL: localhost:%POSTGRES_PORT%
echo PGHero:    http://localhost:%PGHERO_PORT%
echo MinIO:     http://localhost:%MINIO_API_PORT%
echo MinIO UI:  http://localhost:%MINIO_CONSOLE_PORT%
echo.
echo For continuation press any key.
pause >nul
exit /b 0
