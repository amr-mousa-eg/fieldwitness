# FieldWitness autopilot loop
# Runs Claude Code non-interactively, one task per run, again and again.
# Stops when AUTOPILOT_STOP or BLOCKED.md exists in the repo root.
# Waits 30 minutes after a failed run (for example a usage limit), then retries.
#
# Start from the repo root:
#   powershell -ExecutionPolicy Bypass -File scripts\autopilot.ps1
# Stop gracefully: create an empty file named AUTOPILOT_STOP in the repo root.

$ErrorActionPreference = 'Continue'
# Windows PowerShell 5.1 pipes text to native programs as ASCII (non-ASCII prompt characters
# such as em dashes and section signs became '?') and writes '*>' logs as UTF-16 after decoding
# claude's UTF-8 output with the OEM code page (mojibake). Use UTF-8 in both directions.
$utf8 = New-Object System.Text.UTF8Encoding $false
$OutputEncoding = $utf8
[Console]::OutputEncoding = $utf8
$PSDefaultParameterValues['Out-File:Encoding'] = 'utf8'
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

$logDir = Join-Path $repo 'logs\autopilot'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$runsCsv = Join-Path $logDir 'runs.csv'
if (-not (Test-Path $runsCsv)) { Add-Content $runsCsv 'start,end,exit_code,next_sleep_min' }

$failWaitMin = 30   # wait after a failed run (usage limit, network, crash)
$okWaitMin   = 1    # short pause between successful runs
$maxTurns    = 150  # upper bound on agent turns per run

while ($true) {
    if (Test-Path 'AUTOPILOT_STOP') { Write-Host 'AUTOPILOT_STOP found - stopping.'; break }
    if (Test-Path 'BLOCKED.md')     { Write-Host 'BLOCKED.md found - stopping. Read it in the morning.'; break }

    $start = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $runLog = Join-Path $logDir "run-$stamp.log"
    Write-Host "[$start] starting run, log: $runLog"

    Get-Content 'AUTOPILOT_PROMPT.md' -Raw |
        claude -p --permission-mode acceptEdits --max-turns $maxTurns *> $runLog
    $code = $LASTEXITCODE

    $sleepMin = $okWaitMin
    if ($code -ne 0) { $sleepMin = $failWaitMin }
    if (Test-Path 'AUTOPILOT_WAIT') {
        $requested = (Get-Content 'AUTOPILOT_WAIT' -Raw).Trim()
        Remove-Item 'AUTOPILOT_WAIT' -Force
        if ($requested -match '^\d+$') { $sleepMin = [Math]::Max($sleepMin, [int]$requested) }
    }

    $end = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    Add-Content $runsCsv "$start,$end,$code,$sleepMin"
    Write-Host "[$end] run ended with exit code $code - sleeping $sleepMin min"
    Start-Sleep -Seconds ($sleepMin * 60)
}
