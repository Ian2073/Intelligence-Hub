param(
    [string]$AsOf = (Get-Date -Format "yyyy-MM-dd"),
    [switch]$IncludeFuture,
    [switch]$Live,
    [switch]$SkipAcceptance,
    [switch]$CheckScheduledTasks,
    [string]$ScheduledTasksFromCsv = ""
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
$LogFile = Join-Path $LogsDir "hermes-readiness-audit-$Timestamp.log"
$ArgsList = @("scripts\readiness_audit.py", "--as-of", $AsOf)

if ($IncludeFuture) {
    $ArgsList += "--include-future"
}
if ($Live) {
    $ArgsList += "--live"
}
if ($SkipAcceptance) {
    $ArgsList += "--skip-acceptance"
}
if ($CheckScheduledTasks) {
    $ArgsList += "--check-scheduled-tasks"
}
if ($ScheduledTasksFromCsv) {
    $ArgsList += @("--scheduled-tasks-from-csv", $ScheduledTasksFromCsv)
}

Push-Location $ProjectRoot
try {
    & $Python @ArgsList *>&1 | Tee-Object -FilePath $LogFile
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
