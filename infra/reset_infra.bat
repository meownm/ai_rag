@echo off
setlocal enabledelayedexpansion
title rag-infra-reset

echo WARNING: this will delete infra volumes (Postgres and MinIO data).
set /p CONFIRM=Type YES to continue: 
if /I not "%CONFIRM%"=="YES" (
  echo Cancelled.
  echo For continuation press any key.
  pause >nul
  exit /b 0
)

docker compose -f docker-compose.yml down -v
if errorlevel 1 (
  echo Failed to reset infrastructure.
  echo For continuation press any key.
  pause >nul
  exit /b 1
)

echo Reset completed.
echo For continuation press any key.
pause >nul
exit /b 0
