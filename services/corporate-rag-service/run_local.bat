@echo off
setlocal EnableExtensions EnableDelayedExpansion

title Corporate RAG Service - Local Run

set "SERVICE_PORT=8100"
if exist ".env" (
  for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
    if /I "%%~A"=="RAG_SERVICE_PORT" set "SERVICE_PORT=%%~B"
  )
)

echo [INFO] Starting Corporate RAG Service on port !SERVICE_PORT!
poetry run uvicorn app.main:app --host 0.0.0.0 --port !SERVICE_PORT!
if errorlevel 1 goto :error

echo [INFO] Swagger URL: http://localhost:!SERVICE_PORT!/docs
exit /b 0

:error
echo [ERROR] run_local.bat failed.
echo [INFO] Swagger URL (if startup succeeded): http://localhost:!SERVICE_PORT!/docs
pause
exit /b 1
