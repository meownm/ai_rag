@echo off
setlocal enabledelayedexpansion
title rag-infra-stop

echo Stopping infrastructure...
docker compose -f docker-compose.yml down
if errorlevel 1 (
  echo Failed to stop infrastructure.
  echo For continuation press any key.
  pause >nul
  exit /b 1
)

echo Stopped.
echo For continuation press any key.
pause >nul
exit /b 0
