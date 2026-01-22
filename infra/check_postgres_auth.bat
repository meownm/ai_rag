@echo off
setlocal
set "ROOT_DIR=%~dp0.."
set "ENV_FILE=%ROOT_DIR%\.env"
title ai_rag check_postgres_auth

call "%~dp0install_prereqs.bat"
if errorlevel 1 goto :err

call "%~dp0_lib_env.bat" "%ENV_FILE%"
if errorlevel 1 goto :err

if "%PROJECT_NAME%"=="" (
  echo [ERROR] PROJECT_NAME is empty after loading .env: %ENV_FILE%
  echo [HINT] Ensure PROJECT_NAME is present in .env (example: PROJECT_NAME=ai-rag)
  goto :err
)

set "PG_CONT=%PROJECT_NAME%-postgres"

rem Wait for postgres health up to ~90s
set /a _i=0
:wait_loop
docker inspect "%PG_CONT%" --format "{{.State.Health.Status}}" 2>nul | findstr /i "healthy" >nul
if not errorlevel 1 goto :do_check

set /a _i+=1
if %_i% GEQ 90 (
  echo [ERROR] Postgres did not become healthy in time: %PG_CONT%
  goto :err
)
timeout /t 1 /nobreak >nul
goto :wait_loop

:do_check
pushd "%~dp0docker"
if errorlevel 1 goto :err

echo [INFO] Checking Postgres credentials from %ENV_FILE% ...
rem NOTE: CMD groups only by double-quotes, so keep the sh -lc script inside ONE double-quoted argument.
rem Avoid any nested double-quotes inside that argument (they break cmd parsing).
docker compose --env-file "%ENV_FILE%" run --rm db-migrator sh -lc "export PGPASSWORD=$POSTGRES_SUPERPASS; psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_SUPERUSER -d $POSTGRES_DB -v ON_ERROR_STOP=1 -c 'SELECT 1;'" 1>nul
if errorlevel 1 (
  echo [ERROR] Postgres authentication failed using credentials from .env
  echo [HINT] The Postgres password is stored inside the existing volume and does NOT change when you edit .env.
  echo [HINT] Fix options:
  echo   1) For test contour: run infra\reset_all.bat (drops volumes) then infra\deploy_docker_desktop.bat
  echo   2) Or set POSTGRES_SUPERPASS in .env to the original password used when the volume was first created.
  popd
  goto :err
)

popd
echo [INFO] Postgres authentication OK.
endlocal
exit /b 0

:err
echo [ERROR] check_postgres_auth failed.
pause
endlocal
exit /b 1
