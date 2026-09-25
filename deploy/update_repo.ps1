# Pulls the latest code from GitHub; reinstalls dependencies only when requirements.txt changed.
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File deploy\update_repo.ps1 [-Python C:\path\python.exe]
param(
    [string]$ProjectDir = (Split-Path -Parent $PSScriptRoot),
    [string]$Python = ''
)

$ErrorActionPreference = 'Stop'
if (-not $Python) { $Python = Join-Path $ProjectDir '.venv\Scripts\python.exe' }
$logDir = Join-Path $ProjectDir 'logs'
New-Item -ItemType Directory -Force $logDir | Out-Null
$logFile = Join-Path $logDir 'update.log'
$safeDir = $ProjectDir -replace '\\', '/'

function Write-Log([string]$msg) {
    $line = '{0} {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $msg
    Write-Host $line
    Add-Content -Path $logFile -Value $line
}

function Invoke-Git {
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $out = & git -c "safe.directory=$safeDir" @args 2>&1 | ForEach-Object { "$_" }
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prev
    [pscustomobject]@{ Code = $code; Output = ($out -join "`n").Trim() }
}

$failed = $false
try {
    Set-Location $ProjectDir
    $before = (Invoke-Git rev-parse HEAD).Output
    $pull = Invoke-Git pull --ff-only origin main
    if ($pull.Code -ne 0) { throw "git pull failed (exit $($pull.Code)): $($pull.Output)" }
    $after = (Invoke-Git rev-parse HEAD).Output

    if ($before -eq $after) {
        Write-Log ('Already up to date at ' + $after.Substring(0, 7))
    }
    else {
        Write-Log ('Updated {0} -> {1}' -f $before.Substring(0, 7), $after.Substring(0, 7))
        $changed = @((Invoke-Git diff --name-only $before $after).Output -split "`n")
        if ($changed -contains 'requirements.txt') {
            if (-not (Test-Path $Python)) { throw "requirements.txt changed but Python was not found at $Python" }
            $prev = $ErrorActionPreference
            $ErrorActionPreference = 'Continue'
            & $Python -m pip install -r requirements.txt 2>&1 | ForEach-Object { Add-Content -Path $logFile -Value "$_" }
            $pipCode = $LASTEXITCODE
            $ErrorActionPreference = $prev
            if ($pipCode -ne 0) { throw "pip install failed (exit $pipCode), see $logFile" }
            Write-Log 'requirements.txt changed: dependencies reinstalled'
        }
    }
}
catch {
    $failed = $true
    Write-Log "UPDATE FAILED: $($_.Exception.Message)"
}
if ($failed) { exit 1 }
