@echo off
setlocal
title smoke-check-dlq-depth

set MQ_MGMT_PORT=%MQ_MGMT_PORT%
if "%MQ_MGMT_PORT%"=="" set MQ_MGMT_PORT=54041

set MQ_USER=%MQ_USER%
if "%MQ_USER%"=="" set MQ_USER=rag_mq

set MQ_PASSWORD=%MQ_PASSWORD%
if "%MQ_PASSWORD%"=="" set MQ_PASSWORD=rag_mq_pass

set VHOST=%~1
if "%VHOST%"=="" set VHOST=/

set QUEUE=%~2
if "%QUEUE%"=="" (
  echo Usage: smoke_check_dlq_depth.bat ^<vhost^> ^<queue_name^>
  echo Example: smoke_check_dlq_depth.bat / kb.worker.test-worker.dlq
  goto :err
)

set VHOST_ENC=%VHOST%
if "%VHOST%"=="/" set VHOST_ENC=%%2F

powershell -NoProfile -Command ^
  "$u='http://localhost:%MQ_MGMT_PORT%/api/queues/%VHOST_ENC%/%QUEUE%';" ^
  "$pair='%MQ_USER%:%MQ_PASSWORD%';" ^
  "$b=[Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes($pair));" ^
  "$h=@{Authorization=('Basic '+$b)};" ^
  "$r=Invoke-RestMethod -UseBasicParsing -TimeoutSec 5 -Headers $h $u;" ^
  "if($null -eq $r.messages){ exit 1 }" ^
  "Write-Host ('DLQ messages: ' + $r.messages);" ^
  "if([int]$r.messages -gt 0){ exit 2 }"
set RC=%errorlevel%
if %RC%==2 goto :dlq_not_empty
if %RC%==1 goto :err

echo OK
pause
exit /b 0

:dlq_not_empty
echo DLQ NOT EMPTY
pause
exit /b 2

:err
echo ERROR
pause
exit /b 1
