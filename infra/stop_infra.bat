@echo off
setlocal
title ai_rag stop_infra
call "%~dp0stop_all.bat"
exit /b %errorlevel%
