@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "SERVICE_PORT=8100"
if exist ".env" (
  for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
    if /I "%%~A"=="SERVICE_PORT" set "SERVICE_PORT=%%~B"
    if /I "%%~A"=="RAG_SERVICE_PORT" set "SERVICE_PORT=%%~B"
    if /I "%%~A"=="PORT" set "SERVICE_PORT=%%~B"
  )
)

docker build -t corporate-rag-service .
if errorlevel 1 goto :error

docker run -p !SERVICE_PORT!:!SERVICE_PORT! -e SERVICE_PORT=!SERVICE_PORT! corporate-rag-service
if errorlevel 1 goto :error

echo [OK] Deployment finished.
echo [INFO] Swagger URL: http://localhost:!SERVICE_PORT!/docs
exit /b 0

:error
echo [ERROR] deploy_docker_desktop.bat failed.
pause
exit /b 1
