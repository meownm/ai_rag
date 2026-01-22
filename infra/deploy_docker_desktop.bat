@echo off
setlocal
set "ROOT_DIR=%~dp0.."
set "ENV_FILE=%ROOT_DIR%\.env"
set "ENV_EXAMPLE_ROOT=%ROOT_DIR%\.env.example"
set "ENV_EXAMPLE_INFRA=%~dp0\.env.example"

if not exist "%ENV_FILE%" (
  if exist "%ENV_EXAMPLE_ROOT%" (
    copy "%ENV_EXAMPLE_ROOT%" "%ENV_FILE%" >nul
    echo [INFO] Created %ENV_FILE% from %ENV_EXAMPLE_ROOT%
  ) else if exist "%ENV_EXAMPLE_INFRA%" (
    copy "%ENV_EXAMPLE_INFRA%" "%ENV_FILE%" >nul
    echo [INFO] Created %ENV_FILE% from %ENV_EXAMPLE_INFRA%
  ) else (
    echo [ERROR] .env.example not found in root or infra.
    endlocal
    exit /b 1
  )
) else (
  rem .env already exists
)

title ai_rag deploy_docker_desktop

call "%~dp0install_prereqs.bat"
if errorlevel 1 goto :err

call "%~dp0install.bat"
if errorlevel 1 goto :err

call "%~dp0start.bat"
if errorlevel 1 goto :err

call "%~dp0smoke_test.bat"
if errorlevel 1 goto :err

echo [INFO] deploy completed
endlocal
exit /b 0

:err
echo [ERROR] deploy failed.
pause
endlocal
exit /b 1
