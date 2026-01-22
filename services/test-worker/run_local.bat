@echo off
setlocal EnableExtensions EnableDelayedExpansion
title test-worker

if not exist ".env" (
  if exist ".env.example" copy /y ".env.example" ".env" >nul
)

where poetry >nul 2>&1
if errorlevel 1 (
  echo Poetry not found
  pause
  exit /b 1
)

for /f "tokens=2 delims==" %%A in ('findstr /b "APP_PORT=" .env') do set APP_PORT=%%A
if "%APP_PORT%"=="" set APP_PORT=54210

echo Swagger: http://localhost:%APP_PORT%/docs

poetry run uvicorn app.main:app --host 0.0.0.0 --port %APP_PORT%
if errorlevel 1 (
  echo ERROR: service crashed
  pause
  exit /b 1
)

pause
exit /b 0
