# FieldWitness autopilot loop
# Runs Claude Code non-interactively, one task per run, again and again.
# Stops when AUTOPILOT_STOP or BLOCKED.md exists in the repo root.
# Waits 30 minutes after a failed run (for example a usage limit), then retries. A run cut off at
# the turn cap ("Reached max turns" in its log) is a normal end: status "maxturns", 1-minute pause.
# Stops (writes BLOCKED.md) if AUTOPILOT_PROMPT.md is missing or empty.
#
# Start from the repo root:
#   powershell -ExecutionPolicy Bypass -File scripts\autopilot.ps1
# Test one run without looping:
#   powershell -ExecutionPolicy Bypass -File scripts\autopilot.ps1 -MaxTurns 5 -Once
# Stop gracefully: create an empty file named AUTOPILOT_STOP in the repo root.

param(
    [int]$MaxTurns = 150,  # upper bound on agent turns per run
    [switch]$Once          # one run, then exit (no sleep)
)

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
# Absolute path; read with .NET as UTF-8. Get-Content without -Encoding reads a BOM-less file as
# ANSI in PS 5.1, which turned every non-ASCII character of the prompt into mojibake.
$promptPath = Join-Path $repo 'AUTOPILOT_PROMPT.md'

$failWaitMin = 30   # wait after a failed run (usage limit, network, crash)
$okWaitMin   = 1    # short pause between successful runs (and runs cut off at the turn cap)
$maxTurns    = $MaxTurns

while ($true) {
    if (Test-Path 'AUTOPILOT_STOP') { Write-Host 'AUTOPILOT_STOP found - stopping.'; break }
    if (Test-Path 'BLOCKED.md')     { Write-Host 'BLOCKED.md found - stopping. Read it in the morning.'; break }

    $start = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $runLog = Join-Path $logDir "run-$stamp.log"
    Write-Host "[$start] starting run, log: $runLog"

    $prompt = $null
    try { $prompt = [System.IO.File]::ReadAllText($promptPath, $utf8) } catch { $prompt = $null }
    if ([string]::IsNullOrWhiteSpace($prompt)) {
        # Retrying cannot fix a missing prompt: stop instead of failing every 30 minutes.
        $why = "EMPTY PROMPT: $promptPath is missing or empty"
        Write-Host "[$start] $why - writing BLOCKED.md and stopping."
        Add-Content $runLog $why
        Add-Content $runsCsv "$start,$start,EMPTY_PROMPT,0"
        Set-Content -Path (Join-Path $repo 'BLOCKED.md') -Encoding utf8 -Value @(
            '# BLOCKED - autopilot loop: EMPTY PROMPT',
            '',
            "$why (checked $start). The loop stopped instead of retrying.",
            '',
            'Fix: restore the file (git checkout -- AUTOPILOT_PROMPT.md), delete BLOCKED.md and restart the loop.'
        )
        break
    }

    # disableAllHooks: user-level plugin hooks (e.g. caveman) rewrite Bash commands before the
    # permission check, so no allow rule matches them. The project defines no Claude hooks; git's own
    # pre-commit hooks still run. PS 5.1 needs \" to pass the JSON quotes to a native program.
    $prompt | claude -p --model sonnet --settings '{\"disableAllHooks\": true}' --permission-mode acceptEdits --max-turns $maxTurns *> $runLog
    $code = $LASTEXITCODE
    # claude -p exits 1 with "Error: Reached max turns (N)" at the turn cap: a normal end of a run,
    # not a failure, so it gets the short pause. Every other non-zero exit waits 30 minutes.
    $status = "$code"
    if ($code -ne 0 -and (Select-String -Path $runLog -SimpleMatch 'Reached max turns' -Quiet)) {
        $status = 'maxturns'
    }

    $sleepMin = $okWaitMin
    if ($code -ne 0 -and $status -ne 'maxturns') { $sleepMin = $failWaitMin }
    if (Test-Path 'AUTOPILOT_WAIT') {
        $requested = (Get-Content 'AUTOPILOT_WAIT' -Raw).Trim()
        Remove-Item 'AUTOPILOT_WAIT' -Force
        if ($requested -match '^\d+$') { $sleepMin = [Math]::Max($sleepMin, [int]$requested) }
    }

    $end = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    if ($Once) {
        Add-Content $runsCsv "$start,$end,$status,0"
        Write-Host "[$end] run ended with status $status - -Once given, exiting."
        break
    }
    Add-Content $runsCsv "$start,$end,$status,$sleepMin"
    Write-Host "[$end] run ended with status $status - sleeping $sleepMin min"
    Start-Sleep -Seconds ($sleepMin * 60)
}
