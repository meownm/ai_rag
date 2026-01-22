@echo off
setlocal enabledelayedexpansion
title rag-infra-install

echo Checking Docker availability...
docker version >nul 2>&1
if errorlevel 1 (
  echo Docker is not available. Please start Docker Desktop.
  echo For continuation press any key.
  pause >nul
  exit /b 1
)

echo Checking docker compose availability...
docker compose version >nul 2>&1
if errorlevel 1 (
  echo "docker compose" is not available. Please update Docker Desktop.
  echo For continuation press any key.
  pause >nul
  exit /b 1
)

if not exist ".env" (
  echo .env not found. Creating from .env.example
  copy /Y ".env.example" ".env" >nul
  if errorlevel 1 (
    echo Failed to create .env
    echo For continuation press any key.
    pause >nul
    exit /b 1
  )
)

echo Infrastructure install completed (no additional steps).
echo For continuation press any key.
pause >nul
exit /b 0
