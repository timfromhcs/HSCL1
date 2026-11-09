# Build a per-board recovery image (board 201 / 601) without touching a running device.
# Args: -Board 201|601
param([string]$Board = '201')
$ErrorActionPreference = 'Stop'

$env:IDF_TOOLS_PATH = 'E:\esp\tools'
$env:IDF_PATH = 'E:\esp\esp-idf'
$env:IDF_PYTHON_ENV_PATH = 'E:\esp\tools\python_env\idf6.0_py3.14_env'
$env:ESP_IDF_VERSION = '6.0.2'
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:PATH = "$env:IDF_PYTHON_ENV_PATH\Scripts;E:\esp\tools\tools\xtensa-esp-elf\esp-15.2.0_20251204\xtensa-esp-elf\bin;E:\esp\tools\tools\riscv32-esp-elf\esp-15.2.0_20251204\riscv32-esp-elf\bin;E:\esp\tools\tools\cmake\4.0.3\bin;E:\esp\tools\tools\ninja\1.12.1;$env:IDF_PATH\tools;$env:PATH"

$root = 'E:\hcslinux222\artifacts\cross-repos\ESP-Miner'
$out = 'E:\hcslinux222\artifacts\miner\recovery'
New-Item -ItemType Directory -Force -Path $out | Out-Null
Push-Location $root
try {
    & python "$env:IDF_PATH\tools\idf.py" "-DESP_MINER_BOARD_VERSION=$Board" "-DESP_MINER_CONFIG_AP_STUCK=1" build
    if ($LASTEXITCODE -ne 0) { throw "build failed for board $Board" }
    $src = Join-Path $root 'build\esp-miner.bin'
    $dst = Join-Path $out "esp-miner-recovery-$Board.bin"
    Copy-Item -LiteralPath $src -Destination $dst -Force
    $hash = (Get-FileHash -LiteralPath $dst -Algorithm SHA256).Hash.ToLower()
    $size = (Get-Item -LiteralPath $dst).Length
    "$Board`t$size`t$hash" | Add-Content -LiteralPath (Join-Path $out 'SHA256SUMS.txt')
    Write-Output "recovery-$Board : $size bytes sha256=$hash"
} finally {
    Pop-Location
}
