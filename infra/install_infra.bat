@echo off
setlocal
title ai_rag install_infra
call "%~dp0install.bat"
exit /b %errorlevel%
