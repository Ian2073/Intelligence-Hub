param(
    [string]$Start = "",
    [string]$End = "",
    [switch]$PublishNotion,
    [switch]$SendTelegram,
    [switch]$ModelSynthesis,
    [string]$NotionUrl = "local://notion/weekly-dry-run"
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
$LogFile = Join-Path $LogsDir "hermes-weekly-$Timestamp.log"
$ArgsList = @("scripts\run_weekly_intelligence.py", "--notion-url", $NotionUrl)

if ($Start.Trim()) {
    $ArgsList += @("--start", $Start)
}
if ($End.Trim()) {
    $ArgsList += @("--end", $End)
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
