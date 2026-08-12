$ErrorActionPreference = "Stop"

$RootDir = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$SuiteDir = Join-Path $RootDir "tools/autobahn"
$OutputDir = if ($env:OUTPUT_DIR) { $env:OUTPUT_DIR } else { Join-Path $SuiteDir "reports" }
$ConfigDir = Join-Path $OutputDir "config"
$Port = if ($env:PORT) { $env:PORT } else { "18091" }
$Image = if ($env:AUTOBAHN_IMAGE) { $env:AUTOBAHN_IMAGE } else { "crossbario/autobahn-testsuite:latest" }
$ContainerName = if ($env:AUTOBAHN_CONTAINER_NAME) { $env:AUTOBAHN_CONTAINER_NAME } else { "pocketsocket-autobahn" }

New-Item -ItemType Directory -Force -Path $ConfigDir, $OutputDir | Out-Null
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker is required to run the Autobahn testsuite."
}

$Template = Get-Content (Join-Path $SuiteDir "fuzzingclient.template.json") -Raw
$ConfigPath = Join-Path $ConfigDir "fuzzingclient.json"
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($ConfigPath, $Template.Replace("__PORT__", [string]$Port), $Utf8NoBom)

try {
    $Deadline = (Get-Date).AddSeconds(15)
    do {
        Start-Sleep -Milliseconds 100
        $Listening = Test-NetConnection -ComputerName 127.0.0.1 -Port $Port -InformationLevel Quiet
    } while (-not $Listening -and (Get-Date) -lt $Deadline)
    if (-not $Listening) {
        throw "Pocketsocket is not listening on 127.0.0.1:$Port. Start it manually before running this suite."
    }

    & docker rm -f $ContainerName 2>$null | Out-Null
    & docker run --rm --tty --name $ContainerName `
        --add-host "host.docker.internal:host-gateway" `
        --env "PYTHONUNBUFFERED=1" `
        -v "${ConfigDir}:/config:ro" `
        -v "${OutputDir}:/reports" `
        $Image `
        wstest --mode fuzzingclient --spec /config/fuzzingclient.json
    if ($LASTEXITCODE -ne 0) { throw "Autobahn testsuite failed with exit code $LASTEXITCODE" }

    $ReportPath = Join-Path $OutputDir "index.html"
    if (Test-Path $ReportPath -PathType Leaf) {
        Write-Host "Opening report: $ReportPath"
        Start-Process -FilePath $ReportPath
    } else {
        Write-Warning "Autobahn report not found: $ReportPath"
    }
}
finally {
    & docker rm -f $ContainerName 2>$null | Out-Null
}