\
@echo off
setlocal
title rag-platform status

call "%~dp0install_prereqs.bat"
if errorlevel 1 goto :err

call "%~dp0_lib_env.bat" "%~dp0..\..\.env"
if errorlevel 1 goto :err

echo [INFO] Project: %PROJECT_NAME%
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | findstr /i "%PROJECT_NAME%"

echo.
echo [INFO] URLs:
echo   gateway-api:       http://localhost:%GATEWAY_API_HOST_PORT%/docs
echo   ingest-service:    http://localhost:%INGEST_API_HOST_PORT%/docs
echo   search-api:        http://localhost:%SEARCH_API_HOST_PORT%/docs
echo   admin-api:         http://localhost:%ADMIN_API_HOST_PORT%/docs
exit /b 0

:err
echo [ERROR] status failed.
pause
exit /b 1
