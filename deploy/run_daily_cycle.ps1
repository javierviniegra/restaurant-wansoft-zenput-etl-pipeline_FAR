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
# Unbuffered output: a stage that hangs still shows its last line in the log (2026-10-07).
$env:PYTHONUNBUFFERED = '1'
try { [Console]::OutputEncoding = [Text.Encoding]::UTF8 } catch { }

$cycleArgs = @('-m', 'scripts.run_daily_cycle')
if ($Only) { $cycleArgs += @('--only', $Only) }

# Open the log once and share it for reading, so `Get-Content -Wait` from another
# window can follow it; Add-Content per line collided with such readers and lost lines.
$stream = [IO.File]::Open($log, [IO.FileMode]::Append, [IO.FileAccess]::Write, [IO.FileShare]::ReadWrite)
# UTF-8 with BOM (written only when the file is new), so Windows PowerShell's Get-Content reads accents correctly.
$writer = New-Object IO.StreamWriter($stream, (New-Object Text.UTF8Encoding($true)))
$writer.AutoFlush = $true
$ErrorActionPreference = 'Continue'
try {
    & $Python @cycleArgs 2>&1 | ForEach-Object {
        $line = "$_"
        $writer.WriteLine($line)
        Write-Host $line
    }
    $code = $LASTEXITCODE
}
finally {
    $writer.Dispose()
}
$ErrorActionPreference = 'Stop'

Get-ChildItem $logDir -Filter 'daily_cycle_*.log' |
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-$KeepLogDays) } |
    Remove-Item -Force
exit $code
