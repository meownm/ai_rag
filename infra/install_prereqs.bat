\
@echo off
setlocal
title rag-platform install_prereqs

docker version >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Docker is not available. Install Docker Desktop and ensure it is running.
  pause
  exit /b 1
)

docker compose version >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Docker Compose plugin not available. Update Docker Desktop.
  pause
  exit /b 1
)

curl --version >nul 2>&1
if errorlevel 1 (
  echo [ERROR] curl not found.
  pause
  exit /b 1
)

echo [INFO] Prerequisites OK.
exit /b 0
