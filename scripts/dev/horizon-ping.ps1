# Horizon ping - one heartbeat line per minute for long-horizon agent work.
#
# Usage:
#   pwsh -File scripts/dev/horizon-ping.ps1                    # endless, 60 s interval (default)
#   pwsh -File scripts/dev/horizon-ping.ps1 -Minutes 25        # bounded run that completes and notifies
#
# Behaviour:
#   * single instance: a PID file stops a second copy from running
#   * the loop body is guarded, so one bad tick does not end the run
#   * the log rotates at 2 MB to ping.log.1
#   * every tick names the next OPEN row of docs/AUTONOMOUS_QUEUE.md
param(
    [int]$Minutes = 0,
    [int]$IntervalSeconds = 60,
    [string]$Queue = "docs/AUTONOMOUS_QUEUE.md",
    [string]$LogDir = "artifacts/horizon",
    [int]$MaxLogBytes = 2MB
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$logPath = Join-Path $root $LogDir
New-Item -ItemType Directory -Force -Path $logPath | Out-Null
$logFile = Join-Path $logPath "ping.log"
$pidFile = Join-Path $logPath "ping.pid"

# --- single instance -------------------------------------------------------
if (Test-Path $pidFile) {
    $other = 0
    [void][int]::TryParse((Get-Content $pidFile -Raw).Trim(), [ref]$other)
    if ($other -gt 0 -and (Get-Process -Id $other -ErrorAction SilentlyContinue)) {
        Write-Output "horizon-ping: already running as PID $other; this copy exits"
        exit 0
    }
}
Set-Content -Path $pidFile -Value $PID -Encoding ascii

function Write-Tick([string]$text) {
    Write-Output $text
    try {
        if ((Test-Path $logFile) -and ((Get-Item $logFile).Length -gt $MaxLogBytes)) {
            Move-Item -Force $logFile "$logFile.1"
        }
        Add-Content -Path $logFile -Value $text -Encoding utf8
    } catch {
        # logging must never end the loop
    }
}

function Get-NextOpenItem([string]$Path) {
    try {
        if (-not (Test-Path $Path)) { return "queue file missing" }
        $line = Select-String -Path $Path -Pattern '^\|\s*(Q-\d+)\s*\|' |
            Where-Object { $_.Line -match '\|\s*\*{0,2}OPEN' } |
            Select-Object -First 1
        if (-not $line) { return "no OPEN row" }
        $cells = $line.Line.Split('|')
        return "$($cells[1].Trim()) - $($cells[2].Trim())"
    } catch {
        return "queue unreadable"
    }
}

$deadline = if ($Minutes -gt 0) { (Get-Date).AddMinutes($Minutes) } else { [datetime]::MaxValue }
$tick = 0

try {
    while ((Get-Date) -lt $deadline) {
        $tick++
        try {
            $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
            $next = Get-NextOpenItem (Join-Path $root $Queue)
            Write-Tick "[PING $stamp] tick $tick | next: $next"
        } catch {
            Write-Tick "[PING $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] tick $tick | tick failed: $($_.Exception.Message)"
        }
        Start-Sleep -Seconds $IntervalSeconds
    }
} finally {
    Write-Tick "[PING $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] stopped after $tick ticks"
    Remove-Item -Force $pidFile -ErrorAction SilentlyContinue
}
