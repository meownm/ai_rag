@echo off
setlocal
title smoke-batch-jobs

set COUNT=%~1
if "%COUNT%"=="" set COUNT=50

set QUEUE=%~2
if "%QUEUE%"=="" set QUEUE=kb.worker.test-worker

set PROM_PORT=%PROM_PORT%
if "%PROM_PORT%"=="" set PROM_PORT=54060

echo Publishing %COUNT% jobs to %QUEUE%...

if not exist "tools\service_generator\publish_batch_jobs.py" (
  echo tools\service_generator\publish_batch_jobs.py not found
  goto :err
)

python tools\service_generator\publish_batch_jobs.py --queue %QUEUE% --type test-job --count %COUNT%
if errorlevel 1 goto :err

echo Waiting and checking jobs_total...
powershell -NoProfile -Command ^
  "$count=%COUNT%;" ^
  "$prom='http://localhost:%PROM_PORT%/api/v1/query';" ^
  "$deadline=(Get-Date).AddSeconds(20);" ^
  "$ok=0;" ^
  "while((Get-Date) -lt $deadline){" ^
  "  $q=('sum(jobs_total{result=\"ok\",job_type=\"test-job\"})');" ^
  "  $u=$prom+'?query='+[uri]::EscapeDataString($q);" ^
  "  $r=Invoke-RestMethod -UseBasicParsing -TimeoutSec 5 $u;" ^
  "  if($r.status -ne 'success'){ Start-Sleep -Seconds 1; continue }" ^
  "  $v=0; if($r.data.result.Count -gt 0){ $v=[double]$r.data.result[0].value[1] }" ^
  "  if($v -ge $count){ $ok=1; break }" ^
  "  Start-Sleep -Seconds 1" ^
  "}" ^
  "if($ok -ne 1){ exit 1 }"
if errorlevel 1 goto :err

echo OK
pause
exit /b 0

:err
echo ERROR
pause
exit /b 1
