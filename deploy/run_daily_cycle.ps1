# Runs the daily pipeline cycle once, logging to logs\daily_cycle_<yyyyMMdd>.log; exits with the cycle's exit code.
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File deploy\run_daily_cycle.ps1 [-Only "cutover,Inventory"]
param(
    [string]$ProjectDir = (Split-Path -Parent $PSScriptRoot),
    [string]$Python = '',
    [string]$Only = '',
    [int]$KeepLogDays = 30
)

$ErrorActionPreference = 'Stop'
if (-not $Python) { $Python = Join-Path $ProjectDir '.venv\Scripts\python.exe' }
if (-not (Test-Path $Python)) { throw "Python not found: $Python" }
$logDir = Join-Path $ProjectDir 'logs'
New-Item -ItemType Directory -Force $logDir | Out-Null
$log = Join-Path $logDir ('daily_cycle_{0}.log' -f (Get-Date -Format 'yyyyMMdd'))

Set-Location $ProjectDir
$env:PYTHONIOENCODING = 'utf-8'
try { [Console]::OutputEncoding = [Text.Encoding]::UTF8 } catch { }

$cycleArgs = @('-m', 'scripts.run_daily_cycle')
if ($Only) { $cycleArgs += @('--only', $Only) }

$ErrorActionPreference = 'Continue'
& $Python @cycleArgs 2>&1 | ForEach-Object { Add-Content -Path $log -Value "$_" -Encoding UTF8 }
$code = $LASTEXITCODE
$ErrorActionPreference = 'Stop'

Get-ChildItem $logDir -Filter 'daily_cycle_*.log' |
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-$KeepLogDays) } |
    Remove-Item -Force
exit $code
