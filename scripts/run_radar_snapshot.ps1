param(
    [string]$AsOf = "",
    [string]$Since = "",
    [switch]$PublishNotion,
    [switch]$SendTelegram,
    [string]$NotionUrl = "local://notion/radar-dry-run"
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
$LogFile = Join-Path $LogsDir "hermes-radar-$Timestamp.log"
$ArgsList = @("scripts\run_radar_snapshot.py", "--notion-url", $NotionUrl)

if ($AsOf.Trim()) { $ArgsList += @("--as-of", $AsOf) }
if ($Since.Trim()) { $ArgsList += @("--since", $Since) }
if ($PublishNotion) { $ArgsList += "--publish-notion" }
if ($SendTelegram) { $ArgsList += "--send-telegram" }

Push-Location $ProjectRoot
try {
    & $Python @ArgsList *>&1 | Tee-Object -FilePath $LogFile
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
