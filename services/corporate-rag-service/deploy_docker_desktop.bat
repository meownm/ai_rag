@echo off
setlocal EnableExtensions

docker build -t corporate-rag-service .
if errorlevel 1 goto :error

docker run -p 8100:8100 corporate-rag-service
if errorlevel 1 goto :error

echo [OK] Deployment finished.
exit /b 0

:error
echo [ERROR] deploy_docker_desktop.bat failed.
pause
exit /b 1
