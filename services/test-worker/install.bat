@echo off
setlocal EnableExtensions EnableDelayedExpansion
title test-worker-install

if exist "poetry.lock" del /q poetry.lock

where poetry >nul 2>&1
if errorlevel 1 (
  echo Poetry not found. Install Poetry first.
  pause
  exit /b 1
)

poetry install
if errorlevel 1 (
  echo ERROR: poetry install failed
  pause
  exit /b 1
)

echo OK
pause
exit /b 0
