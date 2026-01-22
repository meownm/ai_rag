@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "_ENV_FILE=%~1"
if "%_ENV_FILE%"=="" (
  echo [ERROR] env file path not provided
  exit /b 1
)

if not exist "%_ENV_FILE%" (
  echo [ERROR] Env file not found: %_ENV_FILE%
  exit /b 1
)

set "_TMP=%TEMP%\env_parsed_%RANDOM%.cmd"
> "%_TMP%" echo @echo off

for /f "usebackq delims=" %%L in ("%_ENV_FILE%") do (
  set "line=%%L"

  rem skip empty
  if "!line!"=="" (
    rem noop
  ) else (
    rem skip comments
    if "!line:~0,1!"=="#" (
      rem noop
    ) else (
      rem must contain "="
      echo(!line!| findstr "=" >nul
      if not errorlevel 1 (
        for /f "tokens=1* delims==" %%K in ("!line!") do (
          set "k=%%K"
          set "v=%%L"
          set "v=!v:*==!"

          rem trim key spaces
          for /f "tokens=* delims= " %%A in ("!k!") do set "k=%%A"

          rem remove optional surrounding quotes in value
          if "!v:~0,1!"=="^"" if "!v:~-1!"=="^"" set "v=!v:~1,-1!"

          >>"%_TMP%" echo set "!k!=!v!"
        )
      )
    )
  )
)

call "%_TMP%"
del "%_TMP%" >nul 2>&1

endlocal & exit /b 0
