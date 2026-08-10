$ErrorActionPreference = "Stop"

$RootDir = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$SuiteDir = Join-Path $RootDir "tools/autobahn"
$OutputDir = if ($env:OUTPUT_DIR) { $env:OUTPUT_DIR } else { Join-Path $SuiteDir "reports" }
$ConfigDir = Join-Path $OutputDir "config"
$Port = if ($env:PORT) { $env:PORT } else { "18091" }
$Image = if ($env:AUTOBAHN_IMAGE) { $env:AUTOBAHN_IMAGE } else { "crossbario/autobahn-testsuite:25.10.1" }
$ContainerName = if ($env:AUTOBAHN_CONTAINER_NAME) { $env:AUTOBAHN_CONTAINER_NAME } else { "pocketsocket-autobahn" }
$Cli = if ($env:POCKETSOCKET_CLI) { $env:POCKETSOCKET_CLI } else { Join-Path $RootDir "dist/pocketsocket-cli.exe" }
$ServerLog = Join-Path $OutputDir "pocketsocket.log"
$ServerErrorLog = Join-Path $OutputDir "pocketsocket.stderr.log"
$ServerProcess = $null

New-Item -ItemType Directory -Force -Path $ConfigDir, $OutputDir | Out-Null
if (-not (Test-Path $Cli -PathType Leaf)) {
    throw "Compiled Pocketsocket CLI not found: $Cli. Build it with: cd server; nimble build"
}
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker is required to run the Autobahn testsuite."
}

$Template = Get-Content (Join-Path $SuiteDir "fuzzingclient.template.json") -Raw
$ConfigPath = Join-Path $ConfigDir "fuzzingclient.json"
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($ConfigPath, $Template.Replace("__PORT__", [string]$Port), $Utf8NoBom)

try {
    $Arguments = @("--run", "--print", "--template-dir", (Join-Path $RootDir "server/templates"), "--address", "0.0.0.0", "--port", [string]$Port, "--max-message", "65536")
    $ServerProcess = Start-Process -FilePath $Cli -ArgumentList $Arguments -RedirectStandardOutput $ServerLog -RedirectStandardError $ServerErrorLog -PassThru

    $Deadline = (Get-Date).AddSeconds(15)
    do {
        Start-Sleep -Milliseconds 100
        $Listening = Test-NetConnection -ComputerName 127.0.0.1 -Port $Port -InformationLevel Quiet
    } while (-not $Listening -and (Get-Date) -lt $Deadline -and -not $ServerProcess.HasExited)
    if ($ServerProcess.HasExited) {
        throw "Pocketsocket exited before listening. See $ServerLog"
    }

    & docker rm -f $ContainerName 2>$null | Out-Null
    & docker run --rm --name $ContainerName `
        --add-host "host.docker.internal:host-gateway" `
        -v "${ConfigDir}:/config:ro" `
        -v "${OutputDir}:/reports" `
        $Image `
        wstest --mode fuzzingclient --spec /config/fuzzingclient.json
    if ($LASTEXITCODE -ne 0) { throw "Autobahn testsuite failed with exit code $LASTEXITCODE" }
}
finally {
    & docker rm -f $ContainerName 2>$null | Out-Null
    if ($ServerProcess -and -not $ServerProcess.HasExited) { Stop-Process -Id $ServerProcess.Id -Force }
}