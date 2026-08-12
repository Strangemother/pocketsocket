@echo off
setlocal EnableExtensions

set "ROOT_DIR=%~dp0..\.."
if "%PORT%"=="" set "PORT=18091"
if "%POCKETSOCKET_CLI%"=="" set "POCKETSOCKET_CLI=%ROOT_DIR%\dist\pocketsocket-cli.exe"

if not exist "%POCKETSOCKET_CLI%" (
  echo Compiled Pocketsocket CLI not found: "%POCKETSOCKET_CLI%"
  echo Build it with: cd server ^&^& nimble build
  exit /b 1
)

echo Starting Pocketsocket on 0.0.0.0:%PORT% ...
start "pocketsocket-server" "%POCKETSOCKET_CLI%" --run --print --template-dir "%ROOT_DIR%\server\templates" --address 0.0.0.0 --port %PORT% --max-message 65536
echo Leave the Pocketsocket window running while Autobahn tests execute.