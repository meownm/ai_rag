@echo off
setlocal
cd /d %~dp0
if "%VITE_API_BASE_URL%"=="" set VITE_API_BASE_URL=http://localhost:8100
call npm run dev -- --host 0.0.0.0 --port 5173
endlocal
