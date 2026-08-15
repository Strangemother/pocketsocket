# Restore the Windows build environment and rebuild PocketSocket.
# Run from PowerShell with: .\setup.ps1

[CmdletBinding()]
param(
    [string]$NimVersion = $(if ($env:NIM_VERSION) { $env:NIM_VERSION } else { "2.2.10" })
)

$ErrorActionPreference = "Stop"
$serverRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $serverRoot

$nimRoot = Join-Path $env:LOCALAPPDATA "PocketSocket\nim-$NimVersion"
$nimBin = Join-Path $nimRoot "bin"
$nimbleBin = Join-Path $env:USERPROFILE ".nimble\bin"

function Add-UserPathEntry([string]$PathEntry) {
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $entries = @($userPath -split ";" | Where-Object { $_ })
    if ($entries -notcontains $PathEntry) {
        $entries += $PathEntry
        [Environment]::SetEnvironmentVariable("Path", ($entries -join ";"), "User")
    }
    if (($env:Path -split ";") -notcontains $PathEntry) {
        $env:Path = "$PathEntry;$env:Path"
    }
}

Add-UserPathEntry $nimBin
Add-UserPathEntry $nimbleBin

Write-Host "==> host: $([Environment]::ProcessorCount) logical CPUs"

if (-not (Get-Command nim -ErrorAction SilentlyContinue)) {
    Write-Host "==> nim not found, installing $NimVersion"
    $archive = Join-Path $env:TEMP "nim-$NimVersion-x64.zip"
    $extractPath = Join-Path $env:TEMP "pocketsocket-nim-$NimVersion"
    $downloadUrl = "https://nim-lang.org/download/nim-$NimVersion_x64.zip"

    Write-Host "    downloading $downloadUrl"
    Invoke-WebRequest -Uri $downloadUrl -OutFile $archive
    Remove-Item $extractPath -Recurse -Force -ErrorAction SilentlyContinue
    Expand-Archive -Path $archive -DestinationPath $extractPath -Force
    Remove-Item $archive -Force

    $nimExecutable = Get-ChildItem -Path $extractPath -Filter "nim.exe" -Recurse | Select-Object -First 1
    if (-not $nimExecutable) {
        throw "Nim archive did not contain a bin\nim.exe"
    }
    $extractedRoot = Split-Path -Parent (Split-Path -Parent $nimExecutable.FullName)
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $nimRoot) | Out-Null
    Remove-Item $nimRoot -Recurse -Force -ErrorAction SilentlyContinue
    Move-Item -Path $extractedRoot -Destination $nimRoot
    Remove-Item $extractPath -Recurse -Force -ErrorAction SilentlyContinue
    if (-not (Test-Path (Join-Path $nimBin "nim.exe"))) {
        throw "Nim installation did not contain $nimBin\nim.exe"
    }
}

$nim = Get-Command nim -ErrorAction Stop
Write-Host "==> $(& $nim.Source --version | Select-Object -First 1)"

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    $python = Get-Command python3 -ErrorAction SilentlyContinue
}
if (-not $python) {
    throw "Python was not found. Install Python 3 and ensure it is on PATH."
}
$pythonCommand = $python.Name
$env:POCKETSOCKET_PYTHON = $pythonCommand

Write-Host "==> nim dependencies"
nimble install -d -y

Write-Host "==> benchmark comparison servers"
& $pythonCommand -m pip install --quiet websockets tornado aiohttp fastapi uvicorn

Write-Host "==> building python extension"
nimble buildPyd

Write-Host "==> building standalone cli"
nimble build

Write-Host "==> smoke test"
$smokeTest = @"
import sys
sys.path.insert(0, '../package')
import pocketsocket as ps
missing = [n for n in ps.__all__ if not hasattr(ps, n)]
assert not missing, f'missing exports: {missing}'
print('    python API OK')
"@
& $pythonCommand -c $smokeTest

Write-Host ""
Write-Host "Ready. To run the benchmarks:"
Write-Host ""
Write-Host "    $pythonCommand utils/benchmarks/run_all.py --tag $([Environment]::ProcessorCount)core"
Write-Host ""
Write-Host "Nim was added to your user PATH. Open a new PowerShell window to use it there."