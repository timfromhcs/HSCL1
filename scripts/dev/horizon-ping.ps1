# Horizon ping - keeps a long-horizon agent loop awake with one line per minute.
#
# Usage:
#   pwsh -File scripts/dev/horizon-ping.ps1                 # forever, 60 s interval
#   pwsh -File scripts/dev/horizon-ping.ps1 -Minutes 90     # bounded run
#
# Each tick prints a timestamp, the tick counter and the next OPEN row from
# docs/AUTONOMOUS_QUEUE.md so the loop always has a concrete target.
param(
    [int]$Minutes = 0,
    [int]$IntervalSeconds = 60,
    [string]$Queue = "docs/AUTONOMOUS_QUEUE.md",
    [string]$LogDir = "artifacts/horizon"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$queuePath = Join-Path $root $Queue
$logPath = Join-Path $root $LogDir
New-Item -ItemType Directory -Force -Path $logPath | Out-Null
$logFile = Join-Path $logPath "ping.log"

function Get-NextOpenItem {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return "queue file missing" }
    $line = Select-String -Path $Path -Pattern '^\|\s*(Q-\d+)\s*\|' |
        Where-Object { $_.Line -match '\|\s*\*{0,2}OPEN' } |
        Select-Object -First 1
    if (-not $line) { return "no OPEN row" }
    $cells = $line.Line.Split('|')
    $id = $cells[1].Trim()
    $item = $cells[2].Trim()
    return "$id - $item"
}

$deadline = if ($Minutes -gt 0) { (Get-Date).AddMinutes($Minutes) } else { [datetime]::MaxValue }
$tick = 0

while ((Get-Date) -lt $deadline) {
    $tick++
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $next = Get-NextOpenItem -Path $queuePath
    $line = "[PING $stamp] tick $tick | next: $next"
    Write-Output $line
    Add-Content -Path $logFile -Value $line -Encoding utf8
    Start-Sleep -Seconds $IntervalSeconds
}

$last = "[PING $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] stopped after $tick ticks"
Write-Output $last
Add-Content -Path $logFile -Value $last -Encoding utf8
