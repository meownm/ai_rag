@echo off
setlocal enabledelayedexpansion

set "_ENV_FILE=%~1"
if "%_ENV_FILE%"=="" (
  echo [ERROR] env file path path not provided
  exit /b 1
)

if not exist "%_ENV_FILE%" (
  echo [ERROR] Env file not found: %_ENV_FILE%
  exit /b 1
)

set "_TMP=%TEMP%\env_parsed_%RANDOM%.cmd"
break > "%_TMP%"

for /f "usebackq tokens=* delims=" %%L in ("%_ENV_FILE%") do (
  set "line=%%L"
  if "!line!"=="" goto :continue
  if "!line:~0,1!"=="#" goto :continue
  if /i "!line:~0,7!"=="export " set "line=!line:~7!"
  echo "!line!" | findstr "=" >nul
  if errorlevel 1 goto :continue
  for /f "tokens=1* delims==" %%K in ("!line!") do set "k=%%K"
  set "v=!line:*==!"
  for /f "tokens=* delims= " %%A in ("!k!") do set "k=%%A"
  if "!v:~0,1!"=="^"" (
    if "!v:~-1!"=="^"" set "v=!v:~1,-1!"
  )
  >>"%_TMP%" echo set "!k!=!v!"
  :continue
)

endlocal & call "%_TMP%" & del "%_TMP%" >nul 2>&1
exit /b 0
