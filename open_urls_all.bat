@echo off
setlocal EnableDelayedExpansion
title open-urls-all

if exist "infra\open_urls.bat" call infra\open_urls.bat

echo.
echo Services:

if not exist "tools\service_generator\resolve_ports.py" (
  echo tools\service_generator\resolve_ports.py not found
  goto :end
)

for /f "usebackq tokens=1,2,3,4,5 delims= " %%A in (`python tools\service_generator\resolve_ports.py`) do (
  set SVC=%%A
  set PRT=%%B
  set URL=%%C
  set SRC=%%D
  set WARN=%%E

  set SVC=!SVC:SERVICE=!
  set PRT=!PRT:PORT=!
  set URL=!URL:URL=!
  set SRC=!SRC:SOURCE=!
  set WARN=!WARN:WARN=!

  if "!WARN!"=="1" (
    echo   !SVC! Swagger: !URL!  (WARNING: .env differs from ports_registry)
  ) else (
    echo   !SVC! Swagger: !URL!
  )
)

:end
echo.
pause
exit /b 0
