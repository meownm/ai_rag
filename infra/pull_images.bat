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
)

title ai_rag pull_images

call "%~dp0install_prereqs.bat"
if errorlevel 1 goto :err

pushd "%~dp0docker"
if errorlevel 1 goto :err

echo [INFO] Pulling images...
rem Some Docker Compose versions do not support --progress for pull.
docker compose --env-file "%ENV_FILE%" pull
if errorlevel 1 goto :err

popd
endlocal
exit /b 0

:err
echo [ERROR] pull_images failed.
popd
pause
endlocal
exit /b 1
