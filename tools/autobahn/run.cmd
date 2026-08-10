@echo off
setlocal EnableExtensions

set "ROOT_DIR=%~dp0..\.."
set "SUITE_DIR=%~dp0"
if "%OUTPUT_DIR%"=="" set "OUTPUT_DIR=%SUITE_DIR%reports"
if "%PORT%"=="" set "PORT=18091"
if "%AUTOBAHN_IMAGE%"=="" set "AUTOBAHN_IMAGE=crossbario/autobahn-testsuite:latest"
if "%AUTOBAHN_CONTAINER_NAME%"=="" set "AUTOBAHN_CONTAINER_NAME=pocketsocket-autobahn"
where docker >nul 2>nul || (
  echo Docker is required to run the Autobahn testsuite.
  exit /b 1
)

if not exist "%OUTPUT_DIR%\config" mkdir "%OUTPUT_DIR%\config"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$p = Get-Content -Raw '%SUITE_DIR%fuzzingclient.template.json'; $u = New-Object System.Text.UTF8Encoding($false); [System.IO.File]::WriteAllText('%OUTPUT_DIR%\config\fuzzingclient.json',$p.Replace('__PORT__','%PORT%'),$u)"

echo Waiting for manually started Pocketsocket on 127.0.0.1:%PORT% ...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$d=(Get-Date).AddSeconds(15); do { Start-Sleep -Milliseconds 100; $ok=Test-NetConnection 127.0.0.1 -Port %PORT% -InformationLevel Quiet } while (-not $ok -and (Get-Date) -lt $d); if (-not $ok) { exit 1 }"
if errorlevel 1 (
  echo Pocketsocket is not listening on 127.0.0.1:%PORT%. Start it manually before running this suite.
  exit /b 1
)

docker rm -f "%AUTOBAHN_CONTAINER_NAME%" >nul 2>nul
docker run --rm --name "%AUTOBAHN_CONTAINER_NAME%" ^
  --add-host host.docker.internal:host-gateway ^
  -v "%OUTPUT_DIR%\config:/config:ro" ^
  -v "%OUTPUT_DIR%:/reports" ^
  "%AUTOBAHN_IMAGE%" wstest --mode fuzzingclient --spec /config/fuzzingclient.json
set "STATUS=%ERRORLEVEL%"
exit /b %STATUS%