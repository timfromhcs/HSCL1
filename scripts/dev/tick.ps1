# Work tick - a bounded background command that completes, so the agent is woken every N seconds.
#
# Why not an endless loop: a background command only notifies the agent when it *completes*. An endless
# `while` loop therefore writes to a log but never resurfaces in the conversation. This script sleeps,
# prints one status line and exits; the agent relaunches it, which produces one ping per interval.
#
# Usage:  pwsh -File scripts/dev/tick.ps1 [-Seconds 60]
param(
    [int]$Seconds = 60,
    [string]$Queue = "docs/AUTONOMOUS_QUEUE.md",
    [string]$LogDir = "artifacts/horizon"
)

$ErrorActionPreference = "Continue"
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$logDir = Join-Path $root $LogDir
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$logFile = Join-Path $logDir "tick.log"

Start-Sleep -Seconds $Seconds

function Get-NextOpenItem {
    param([string]$Path)
    try {
        if (-not (Test-Path $Path)) { return "queue missing" }
        $line = Select-String -Path $Path -Pattern '^\|\s*(Q-\d+)\s*\|' |
            Where-Object { $_.Line -match '\|\s*\*{0,2}OPEN' } |
            Select-Object -First 1
        if (-not $line) { return "no OPEN row" }
        $cells = $line.Line.Split('|')
        return "$($cells[1].Trim()) - $($cells[2].Trim())"
    } catch { return "queue unreadable" }
}

$next = Get-NextOpenItem (Join-Path $root $Queue)
$free = try { "{0:N0} GB free on E:" -f ((Get-PSDrive E).Free / 1GB) } catch { "disk unknown" }
$line = "[TICK $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] next: $next | $free"

if ((Test-Path $logFile) -and ((Get-Item $logFile).Length -gt 1MB)) {
    Move-Item -Force $logFile "$logFile.1"
}
Add-Content -Path $logFile -Value $line -Encoding utf8
Write-Output $line
