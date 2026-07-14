param(
    [switch]$Apply,
    [switch]$UpdateEnv,
    [switch]$PrintPayloads
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
$LogFile = Join-Path $LogsDir "hermes-notion-provision-$Timestamp.log"
$ArgsList = @("scripts\provision_notion_workspace.py")

if ($Apply) {
    $ArgsList += "--apply"
}
if ($UpdateEnv) {
    $ArgsList += "--update-env"
}
if ($PrintPayloads) {
    $ArgsList += "--print-payloads"
}

Push-Location $ProjectRoot
try {
    & $Python @ArgsList *>&1 | Tee-Object -FilePath $LogFile
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
