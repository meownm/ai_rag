@echo off
setlocal
title ai_rag reset_infra
call "%~dp0reset_all.bat"
exit /b %errorlevel%
