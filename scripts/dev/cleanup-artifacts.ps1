# Delete only regenerable build artefacts under artifacts/, and never evidence.
#
# Written after the 2026-11-13 incident: a cleanup that used `Get-ChildItem -LiteralPath ... -Recurse -Include`
# under Windows PowerShell 5.1 deleted the whole 124 GB artifacts tree, because 5.1 ignores -Include with
# -LiteralPath and returns every file. This script therefore:
#   * never uses -Include (it filters with Where-Object on explicit extensions),
#   * is a DRY RUN unless -Apply is passed,
#   * prints the exact list and the total before deleting,
#   * protects every evidence extension (.json/.png/.md/.log/.txt/.yml/.yaml/.spdx),
#   * keeps the newest ISO and the newest release-part set.
#
# Usage:
#   powershell -File scripts/dev/cleanup-artifacts.ps1              # dry run, prints what would go
#   powershell -File scripts/dev/cleanup-artifacts.ps1 -Apply       # delete
param(
    [string]$Root = 'E:\hcslinux222\artifacts',
    [switch]$Apply
)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $Root)) { throw "artifacts root not found: $Root" }

$evidence = @('.json', '.png', '.md', '.log', '.txt', '.yml', '.yaml', '.spdx', '.html')
$diskExt = @('.qcow2', '.raw', '.img')

$all = Get-ChildItem -LiteralPath $Root -Recurse -File -ErrorAction SilentlyContinue
if (-not $all) { "nothing under $Root"; exit 0 }

# 1. Disposable VM disks.
$disks = $all | Where-Object { $diskExt -contains $_.Extension.ToLower() }

# 2. ISOs: keep the newest, delete older ones and their sidecars/parts.
$isos = $all | Where-Object { $_.Extension.ToLower() -eq '.iso' -and $_.Name -like 'HSCL1-*' } | Sort-Object LastWriteTime -Descending
$keepIso = $isos | Select-Object -First 1
$oldIso = $isos | Select-Object -Skip 1
$isoNames = @()
foreach ($i in $oldIso) { $isoNames += $i.Name }
$isoSidecars = $all | Where-Object {
    $n = $_.Name
    $hit = $false
    foreach ($o in $isoNames) { if ($n -like "$o*") { $hit = $true } }
    $hit
}

# 3. Release sets: keep the newest directory, delete older ones (ISOs, parts, sums, notes).
$sets = Get-ChildItem -LiteralPath $Root -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -like 'release-*-set' } | Sort-Object LastWriteTime -Descending
$oldSets = $sets | Select-Object -Skip 1
$setFiles = @()
foreach ($s in $oldSets) {
    $setFiles += Get-ChildItem -LiteralPath $s.FullName -Recurse -File -ErrorAction SilentlyContinue
}

$targets = @($disks) + @($isoSidecars) + @($setFiles) | Sort-Object FullName -Unique
$targets = $targets | Where-Object { $evidence -notcontains $_.Extension.ToLower() }
$targets = $targets | Where-Object { -not ($keepIso -and $_.FullName -eq $keepIso.FullName) }

if (-not $targets) { "nothing to delete under $Root"; exit 0 }

$total = ($targets | Measure-Object Length -Sum).Sum
"== plan: $($targets.Count) files, $([math]::Round($total/1GB,2)) GB"
foreach ($t in $targets) { '{0,12}  {1}' -f $t.Length, $t.FullName }
if (-not $Apply) {
    ''
    'dry run only: pass -Apply to delete exactly the files above'
    exit 0
}
foreach ($t in $targets) { Remove-Item -LiteralPath $t.FullName -Force }
foreach ($s in $oldSets) {
    if ((Get-ChildItem -LiteralPath $s.FullName -Force -ErrorAction SilentlyContinue | Measure-Object).Count -eq 0) {
        Remove-Item -LiteralPath $s.FullName -Force
    }
}
"deleted $($targets.Count) files, $([math]::Round($total/1GB,2)) GB; free on drive: $([math]::Round((Get-PSDrive ((Get-Item $Root).PSDrive.Name)).Free/1GB,2)) GB"
