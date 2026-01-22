@echo off
setlocal
title ai_rag start_infra
call "%~dp0start.bat"
exit /b %errorlevel%
