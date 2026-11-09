# Bake the home Wi-Fi credentials into the per-unit firmware defaults.
# The password is read from the Windows WLAN profile and written to sdkconfig only;
# it is never printed.
param(
    [string]$Ssid = 'FRITZ!Box 7590 MP-2,4GhZ',
    [string]$Config = 'E:\hcslinux222\artifacts\cross-repos\ESP-Miner\sdkconfig'
)
$ErrorActionPreference = 'Stop'

$profile = netsh wlan show profile name="$Ssid" key=clear
# Match ASCII-only: the script is read as ANSI, so a literal umlaut would not match.
$keyLine = $profile | Where-Object { $_ -match 'sselinhalt\s*:' -or $_ -match 'Key Content\s*:' }
if (-not $keyLine) { Write-Output 'ERROR: no key content line'; exit 2 }
$pwd = ($keyLine -split ':', 2)[1].Trim()
if (-not $pwd) { Write-Output 'ERROR: empty key'; exit 2 }

function Esc([string]$v) { $v.Replace('\', '\\').Replace('"', '\"') }

$lines = Get-Content -LiteralPath $Config -Encoding UTF8
function Set-Key([string[]]$src, [string]$key, [string]$value) {
    $entry = "$key=`"$value`""
    $found = $false
    $out = foreach ($l in $src) {
        if ($l -like "$key=*") { $found = $true; $entry } else { $l }
    }
    if (-not $found) { $out += $entry }
    return $out
}
$lines = Set-Key $lines 'CONFIG_ESP_WIFI_SSID' (Esc $Ssid)
$lines = Set-Key $lines 'CONFIG_ESP_WIFI_PASSWORD' (Esc $pwd)
$lines = Set-Key $lines 'CONFIG_LWIP_LOCAL_HOSTNAME' 'timsminer'
Set-Content -LiteralPath $Config -Value $lines -Encoding UTF8
Write-Output ("patched: ssid set, password set ({0} chars), hostname timsminer" -f $pwd.Length)
