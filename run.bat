@echo off
setlocal EnableExtensions EnableDelayedExpansion
title rag-runner

if "%~1"=="" goto :menu

set CMD=%~1
shift

if /I "%CMD%"=="infra" goto :infra
if /I "%CMD%"=="verify" goto :verify
if /I "%CMD%"=="smoke" goto :smoke
if /I "%CMD%"=="urls" goto :urls
if /I "%CMD%"=="service" goto :service
if /I "%CMD%"=="worker" goto :worker
if /I "%CMD%"=="test-worker" goto :test_worker
if /I "%CMD%"=="help" goto :help

echo Unknown command: %CMD%
goto :help

:menu
echo.
echo RAG Runner
echo 1) Infra up
echo 2) Verify (--fix + report)
echo 3) Smoke (cleanup + batch + dlq empty)
echo 4) Open URLs
echo 5) Run service (select)
echo 6) Run worker (select)
echo 7) Run test-worker
echo 8) Help
echo 0) Exit
echo.
set /p CH=Select:
if "%CH%"=="1" goto :infra
if "%CH%"=="2" goto :verify
if "%CH%"=="3" goto :smoke
if "%CH%"=="4" goto :urls
if "%CH%"=="5" goto :service_select
if "%CH%"=="6" goto :worker_select
if "%CH%"=="7" goto :test_worker
if "%CH%"=="8" goto :help
if "%CH%"=="0" goto :eof
goto :menu

:infra
if exist "infra\run_infra_up.bat" (
  call infra\run_infra_up.bat
  exit /b %errorlevel%
)
echo infra\run_infra_up.bat not found
pause
exit /b 1

:verify
if exist "verify_infra_consistency.bat" (
  call verify_infra_consistency.bat --fix
  exit /b %errorlevel%
)
echo verify_infra_consistency.bat not found
pause
exit /b 1

:smoke
if exist "smoke_test_all.bat" (
  call smoke_test_all.bat
  exit /b %errorlevel%
)
echo smoke_test_all.bat not found
pause
exit /b 1

:urls
if exist "open_urls_all.bat" (
  call open_urls_all.bat
  exit /b %errorlevel%
)
echo open_urls_all.bat not found
pause
exit /b 1

:test_worker
call :worker test-worker
exit /b %errorlevel%

:service
if "%~1"=="" goto :service_select
set SVC=%~1
if exist "services\%SVC%\run_local.bat" (
  pushd "services\%SVC%"
  call run_local.bat
  set RC=%errorlevel%
  popd
  exit /b %RC%
)
echo services\%SVC%\run_local.bat not found
pause
exit /b 1

:worker
if "%~1"=="" goto :worker_select
set WRK=%~1
if exist "services\%WRK%\run_local.bat" (
  pushd "services\%WRK%"
  call run_local.bat
  set RC=%errorlevel%
  popd
  exit /b %RC%
)
echo services\%WRK%\run_local.bat not found
pause
exit /b 1

:service_select
call :list_services
echo.
set /p SVC=Service name:
goto :service

:worker_select
call :list_services
echo.
set /p WRK=Worker name:
goto :worker

:list_services
echo.
echo Available under services\:
for /d %%D in ("services\*") do (
  echo   %%~nxD
)
exit /b 0

:help
echo.
echo Commands:
echo   run.bat infra
echo   run.bat verify
echo   run.bat smoke
echo   run.bat urls
echo   run.bat service ^<name^>
echo   run.bat worker ^<name^>
echo   run.bat test-worker
echo.
pause
exit /b 0
