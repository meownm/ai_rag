@echo off
rem -----------------------------------------------------------------------------
rem _lib_env.bat
rem Loads KEY=VALUE pairs from a .env file into the CURRENT cmd.exe environment.
rem Safe for values containing &, |, <, > because we always use: set "K=V"
rem Ignores:
rem - empty lines
rem - lines starting with #
rem Notes:
rem - does not support multiline values
rem - does not support "export KEY=VALUE" syntax (keep plain KEY=VALUE)
rem -----------------------------------------------------------------------------

set "_ENV_FILE=%~1"
if "%_ENV_FILE%"=="" (
  echo [ERROR] Env file path not provided.
  exit /b 1
)

if not exist "%_ENV_FILE%" (
  echo [ERROR] Env file not found: %_ENV_FILE%
  exit /b 1
)

for /f "usebackq delims=" %%L in ("%_ENV_FILE%") do (
  call :_process_line "%%L"
)

exit /b 0

:_process_line
setlocal EnableExtensions
set "line=%~1"

rem trim leading spaces
for /f "tokens=* delims= " %%A in ("%line%") do set "line=%%A"

if "%line%"=="" ( endlocal & goto :eof )
if "%line:~0,1%"=="#" ( endlocal & goto :eof )

rem must contain '='
echo(%line%| findstr "=" >nul
if errorlevel 1 ( endlocal & goto :eof )

for /f "tokens=1* delims==" %%K in ("%line%") do (
  set "k=%%K"
  set "v=%%L"
)

rem v is whole line, strip key part including first '='
for /f "tokens=1* delims==" %%X in ("%line%") do set "v=%%Y"

rem trim key spaces
for /f "tokens=* delims= " %%A in ("%k%") do set "k=%%A"

if "%k%"=="" ( endlocal & goto :eof )

rem remove surrounding quotes in value
if not "%v%"=="" (
  if "%v:~0,1%"=="^"" if "%v:~-1%"=="^"" set "v=%v:~1,-1%"
)

endlocal & set "%k%=%v%"
goto :eof
