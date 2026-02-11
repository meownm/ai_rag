@echo off
setlocal
cd /d %~dp0
if "%VITE_API_BASE_URL%"=="" set VITE_API_BASE_URL=http://host.docker.internal:8100
docker build --build-arg VITE_API_BASE_URL=%VITE_API_BASE_URL% -t corporate-rag-frontend:local .
docker run --rm -p 8080:80 --name corporate-rag-frontend corporate-rag-frontend:local
endlocal
