param(
    [string]$AsOf = "",
    [string]$WindowStart = "",
    [switch]$PublishNotion,
    [switch]$SendTelegram,
    [switch]$ModelSynthesis,
    [string]$NotionUrl = "local://notion/dashboard-dry-run"
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
$LogFile = Join-Path $LogsDir "hermes-dashboard-$Timestamp.log"
$ArgsList = @("scripts\run_executive_dashboard.py", "--notion-url", $NotionUrl)

if ($AsOf.Trim()) {
    $ArgsList += @("--as-of", $AsOf)
}
if ($WindowStart.Trim()) {
    $ArgsList += @("--window-start", $WindowStart)
}
if ($PublishNotion) {
    $ArgsList += "--publish-notion"
}
if ($SendTelegram) {
    $ArgsList += "--send-telegram"
}
if ($ModelSynthesis) {
    $ArgsList += "--model-synthesis"
}

Push-Location $ProjectRoot
try {
    & $Python @ArgsList *>&1 | Tee-Object -FilePath $LogFile
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
