param(
    [string]$Date = "",
    [switch]$LiveGitHub,
    [switch]$LivePapers,
    [switch]$LivePapersWithCode,
    [switch]$LiveDomainRss,
    [switch]$PublishNotion,
    [switch]$SendTelegram,
    [switch]$ModelSynthesis,
    [switch]$Weekly,
    [switch]$Monthly,
    [switch]$NoDashboard,
    [switch]$NoRadar,
    [string]$NotionUrl = "local://notion/orchestration-dry-run"
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
$LogFile = Join-Path $LogsDir "hermes-orchestration-$Timestamp.log"
$ArgsList = @("scripts\run_hermes_orchestration.py", "--notion-url", $NotionUrl)

if ($Date.Trim()) { $ArgsList += @("--date", $Date) }
if ($LiveGitHub) { $ArgsList += "--live-github" }
if ($LivePapers) { $ArgsList += "--live-papers" }
if ($LivePapersWithCode) { $ArgsList += "--live-papers-with-code" }
if ($LiveDomainRss) { $ArgsList += "--live-domain-rss" }
if ($PublishNotion) { $ArgsList += "--publish-notion" }
if ($SendTelegram) { $ArgsList += "--send-telegram" }
if ($ModelSynthesis) { $ArgsList += "--model-synthesis" }
if ($Weekly) { $ArgsList += "--weekly" }
if ($Monthly) { $ArgsList += "--monthly" }
if ($NoDashboard) { $ArgsList += "--no-dashboard" }
if ($NoRadar) { $ArgsList += "--no-radar" }

Push-Location $ProjectRoot
try {
    & $Python @ArgsList *>&1 | Tee-Object -FilePath $LogFile
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
