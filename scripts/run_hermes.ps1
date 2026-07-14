param(
    [string]$Topic = "",
    [switch]$SmokeTest
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")
$Python = Join-Path $ProjectRoot "hub_env\Scripts\python.exe"
$LogsDir = Join-Path $ProjectRoot "logs"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Python virtual environment not found: $Python"
}

if (-not (Test-Path -LiteralPath $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir | Out-Null
}

$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$LogFile = Join-Path $LogsDir "hermes-$Timestamp.log"

Push-Location $ProjectRoot
try {
    if ($SmokeTest) {
        & $Python "scripts\smoke_test.py" *>&1 | Tee-Object -FilePath $LogFile
        exit $LASTEXITCODE
    }

    if ($Topic.Trim()) {
        & $Python "main.py" --topic $Topic *>&1 | Tee-Object -FilePath $LogFile
    }
    else {
        & $Python "main.py" *>&1 | Tee-Object -FilePath $LogFile
    }
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
