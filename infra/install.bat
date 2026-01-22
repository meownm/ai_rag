@echo off
setlocal
title ai_rag infra install

call "%~dp0install_prereqs.bat"
if errorlevel 1 goto :err

if not exist "..\.env" (
  if exist "..\.env.example" (
    copy "..\.env.example" "..\.env" >nul
    echo [INFO] Created ..\.env from ..\.env.example
  ) else (
    echo [ERROR] ..\.env.example not found.
    goto :err
  )
) else (
  echo [INFO] ..\.env already exists
)

exit /b 0

:err
echo [ERROR] install failed.
pause
exit /b 1
