# Permanent heartbeat: writes one line every 120 s and never exits on its own.
# Used as the visible "ping" trail; the agent is woken by a separate 2-minute one-shot because the
# harness only notifies on command completion.
$ErrorActionPreference = 'Continue'
$out = Join-Path $PSScriptRoot '..\..\artifacts\heartbeat\ticks.log'
$dir = Split-Path -Parent $out
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$n = 0
while ($true) {
    $n++
    $stamp = (Get-Date).ToString('yyyy-MM-ddTHH:mm:ss')
    Add-Content -LiteralPath $out -Value "$stamp tick=$n pid=$PID"
    Write-Output "AGENT_HEARTBEAT $stamp tick=$n"
    Start-Sleep -Seconds 120
}
