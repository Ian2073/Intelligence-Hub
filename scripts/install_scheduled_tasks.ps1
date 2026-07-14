param(
    [ValidateSet("Install", "Remove")]
    [string]$Action = "Install",
    [string]$DailyTime = "08:00",
    [string]$WeeklyTime = "08:15",
    [string]$MonthlyTime = "08:30",
    [string]$DashboardTime = "08:45",
    [string]$RadarTime = "08:50",
    [string]$DecisionReviewTime = "08:55",
    [switch]$LiveGitHub,
    [switch]$LivePapers,
    [switch]$LivePapersWithCode,
    [switch]$LiveDomainRss,
    [switch]$PublishNotion,
    [switch]$SendTelegram,
    [switch]$ModelSynthesis,
    [switch]$IncludeWeekly,
    [switch]$IncludeMonthly,
    [switch]$IncludeDashboard,
    [switch]$IncludeRadar,
    [switch]$IncludeDecisionReview,
    [switch]$LiveGoLiveCheck,
    [switch]$SkipGoLiveCheck,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")
$OrchestrationScript = Join-Path $ProjectRoot "scripts\run_hermes_orchestration.ps1"
$WeeklyScript = Join-Path $ProjectRoot "scripts\run_weekly_intelligence.ps1"
$MonthlyScript = Join-Path $ProjectRoot "scripts\run_monthly_intelligence.ps1"
$DashboardScript = Join-Path $ProjectRoot "scripts\run_executive_dashboard.ps1"
$RadarScript = Join-Path $ProjectRoot "scripts\run_radar_snapshot.ps1"
$DecisionReviewScript = Join-Path $ProjectRoot "scripts\run_decision_review.ps1"
$Python = Join-Path $ProjectRoot "hub_env\Scripts\python.exe"

function Join-Flags {
    param([string[]]$Flags)
    if ($Flags.Count -eq 0) { return "" }
    return " " + ($Flags -join " ")
}

function New-TaskCommand {
    param(
        [string]$ScriptPath,
        [string[]]$Flags
    )
    $flagText = Join-Flags -Flags $Flags
    return "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`"$flagText"
}

function Format-CommandPreview {
    param([string[]]$CommandArgs)
    $formatted = foreach ($arg in $CommandArgs) {
        if ($arg -match '\s|"' ) {
            '"' + ($arg -replace '"', '\"') + '"'
        }
        else {
            $arg
        }
    }
    return "schtasks.exe " + ($formatted -join " ")
}

function Install-Task {
    param(
        [string]$Name,
        [string]$Schedule,
        [string]$Time,
        [string]$Command,
        [string[]]$ExtraArgs = @()
    )
    $args = @("/Create", "/TN", $Name, "/SC", $Schedule, "/ST", $Time, "/TR", $Command, "/F")
    $args += $ExtraArgs
    if ($DryRun) {
        Write-Output ("DRY-RUN install: " + (Format-CommandPreview -CommandArgs $args))
        return
    }
    & schtasks.exe @args | Out-Host
}

function Remove-Task {
    param([string]$Name)
    if ($DryRun) {
        Write-Output ("DRY-RUN remove: " + (Format-CommandPreview -CommandArgs @("/Delete", "/TN", $Name, "/F")))
        return
    }
    & schtasks.exe /Delete /TN $Name /F | Out-Host
}

function Test-ProductionInstall {
    return [bool](
        $LiveGitHub -or
        $LivePapers -or
        $LivePapersWithCode -or
        $LiveDomainRss -or
        $PublishNotion -or
        $SendTelegram -or
        $ModelSynthesis
    )
}

function Invoke-GoLiveGate {
    if ($Action -ne "Install" -or $DryRun -or $SkipGoLiveCheck -or -not (Test-ProductionInstall)) {
        return
    }
    if (-not (Test-Path -LiteralPath $Python)) {
        throw "Python virtual environment not found: $Python"
    }
    $gateArgs = @("scripts\go_live_check.py")
    if ($LiveGoLiveCheck) {
        $gateArgs += "--live"
    }
    Push-Location $ProjectRoot
    try {
        & $Python @gateArgs
        if ($LASTEXITCODE -ne 0) {
            throw "Go-live gate failed. Fix the failed checks, rerun with -DryRun for preview, or pass -SkipGoLiveCheck to override intentionally."
        }
    }
    finally {
        Pop-Location
    }
}

$liveFlags = @()
if ($LiveGitHub) { $liveFlags += "-LiveGitHub" }
if ($LivePapers) { $liveFlags += "-LivePapers" }
if ($LivePapersWithCode) { $liveFlags += "-LivePapersWithCode" }
if ($LiveDomainRss) { $liveFlags += "-LiveDomainRss" }
if ($PublishNotion) { $liveFlags += "-PublishNotion" }
if ($SendTelegram) { $liveFlags += "-SendTelegram" }
if ($ModelSynthesis) { $liveFlags += "-ModelSynthesis" }

$publishFlags = @()
if ($PublishNotion) { $publishFlags += "-PublishNotion" }
if ($SendTelegram) { $publishFlags += "-SendTelegram" }

$synthesisPublishFlags = @()
if ($PublishNotion) { $synthesisPublishFlags += "-PublishNotion" }
if ($SendTelegram) { $synthesisPublishFlags += "-SendTelegram" }
if ($ModelSynthesis) { $synthesisPublishFlags += "-ModelSynthesis" }

$tasks = @(
    @{
        Name = "Intelligence Hub Daily"
        Schedule = "DAILY"
        Time = $DailyTime
        Command = New-TaskCommand -ScriptPath $OrchestrationScript -Flags ($liveFlags + @("-NoDashboard"))
        ExtraArgs = @()
    }
)

if ($IncludeWeekly) {
    $tasks += @{
        Name = "Intelligence Hub Weekly"
        Schedule = "WEEKLY"
        Time = $WeeklyTime
        Command = New-TaskCommand -ScriptPath $WeeklyScript -Flags $synthesisPublishFlags
        ExtraArgs = @("/D", "MON")
    }
}

if ($IncludeMonthly) {
    $tasks += @{
        Name = "Intelligence Hub Monthly"
        Schedule = "MONTHLY"
        Time = $MonthlyTime
        Command = New-TaskCommand -ScriptPath $MonthlyScript -Flags $synthesisPublishFlags
        ExtraArgs = @("/D", "1")
    }
}

if ($IncludeDashboard) {
    $tasks += @{
        Name = "Intelligence Hub Dashboard"
        Schedule = "DAILY"
        Time = $DashboardTime
        Command = New-TaskCommand -ScriptPath $DashboardScript -Flags $synthesisPublishFlags
        ExtraArgs = @()
    }
}

if ($IncludeRadar) {
    $tasks += @{
        Name = "Intelligence Hub Radar"
        Schedule = "DAILY"
        Time = $RadarTime
        Command = New-TaskCommand -ScriptPath $RadarScript -Flags $publishFlags
        ExtraArgs = @()
    }
}

if ($IncludeDecisionReview) {
    $tasks += @{
        Name = "Intelligence Hub Decision Review"
        Schedule = "WEEKLY"
        Time = $DecisionReviewTime
        Command = New-TaskCommand -ScriptPath $DecisionReviewScript -Flags $publishFlags
        ExtraArgs = @("/D", "MON")
    }
}

Invoke-GoLiveGate

foreach ($task in $tasks) {
    if ($Action -eq "Install") {
        Install-Task -Name $task.Name -Schedule $task.Schedule -Time $task.Time -Command $task.Command -ExtraArgs $task.ExtraArgs
    }
    else {
        Remove-Task -Name $task.Name
    }
}
