@echo off
setlocal
title smoke-cleanup-queues

set MQ_MGMT_PORT=%MQ_MGMT_PORT%
if "%MQ_MGMT_PORT%"=="" set MQ_MGMT_PORT=54041

set MQ_USER=%MQ_USER%
if "%MQ_USER%"=="" set MQ_USER=rag_mq

set MQ_PASSWORD=%MQ_PASSWORD%
if "%MQ_PASSWORD%"=="" set MQ_PASSWORD=rag_mq_pass

set VHOST=%~1
if "%VHOST%"=="" set VHOST=/

set QUEUE_MAIN=%~2
if "%QUEUE_MAIN%"=="" set QUEUE_MAIN=kb.worker.test-worker

set VHOST_ENC=%VHOST%
if "%VHOST%"=="/" set VHOST_ENC=%%2F

set QRETRY=%QUEUE_MAIN%.retry
set QDLQ=%QUEUE_MAIN%.dlq

echo Purging queues:
echo   %QUEUE_MAIN%
echo   %QRETRY%
echo   %QDLQ%

call :purge %VHOST_ENC% %QUEUE_MAIN%
call :purge %VHOST_ENC% %QRETRY%
call :purge %VHOST_ENC% %QDLQ%

echo OK
exit /b 0

:purge
set VHE=%~1
set QN=%~2

powershell -NoProfile -Command ^
  "$u='http://localhost:%MQ_MGMT_PORT%/api/queues/%VHE%/%QN%/contents';" ^
  "$pair='%MQ_USER%:%MQ_PASSWORD%';" ^
  "$b=[Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes($pair));" ^
  "$h=@{Authorization=('Basic '+$b)};" ^
  "try{ Invoke-RestMethod -Method Delete -UseBasicParsing -TimeoutSec 5 -Headers $h $u | Out-Null; exit 0 } catch { exit 0 }"
exit /b 0
