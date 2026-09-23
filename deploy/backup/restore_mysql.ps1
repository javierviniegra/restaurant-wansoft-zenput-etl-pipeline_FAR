# Restores one database from a backup folder into a staging database. Refuses to overwrite live databases.
# Usage: restore_mysql.ps1 -BackupFolder C:\Backups\mysql\20260927_073000 -SourceDatabase wansoft -TargetDatabase wansoft_prueba
# Needs a config file for a user that can create databases and set definers (e.g. root).
param(
    [Parameter(Mandatory = $true)] [string]$BackupFolder,
    [Parameter(Mandatory = $true)] [string]$SourceDatabase,
    [Parameter(Mandatory = $true)] [string]$TargetDatabase,
    [string]$ConfigFile = 'C:\Backups\mysql\restore.cnf',
    [string]$MysqlBin = '',
    [string[]]$ProtectedDatabases = @('wansoft', 'zenput', 'odoo', 'presupuestos_ap', 'mysql', 'information_schema', 'performance_schema', 'sys')
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression

if ($ProtectedDatabases -contains $TargetDatabase.ToLower()) {
    throw "Refusing to restore onto protected database '$TargetDatabase'. Use a staging name such as ${SourceDatabase}_prueba."
}
$gz = Join-Path $BackupFolder "$SourceDatabase.sql.gz"
if (-not (Test-Path $gz)) { throw "Backup file not found: $gz" }
if (-not (Test-Path $ConfigFile)) { throw "Config file not found: $ConfigFile" }

function Find-MysqlClient {
    $candidates = @()
    if ($MysqlBin) { $candidates += Join-Path $MysqlBin 'mysql.exe' }
    $candidates += 'C:\xampp\mysql\bin\mysql.exe'
    $proc = Get-Process mysqld, mariadbd -ErrorAction SilentlyContinue | Where-Object { $_.Path } | Select-Object -First 1
    if ($proc) { $candidates += Join-Path (Split-Path $proc.Path) 'mysql.exe' }
    $cmd = Get-Command mysql.exe -ErrorAction SilentlyContinue
    if ($cmd) { $candidates += $cmd.Source }
    foreach ($c in $candidates) { if (Test-Path $c) { return $c } }
    throw 'mysql.exe not found. Pass -MysqlBin with the folder that contains it.'
}

$mysql = Find-MysqlClient
$tmp = Join-Path $BackupFolder "$SourceDatabase.restore_tmp.sql"
$sw = [Diagnostics.Stopwatch]::StartNew()
try {
    Write-Host "Decompressing $gz ..."
    $in = [IO.File]::OpenRead($gz)
    try {
        $out = [IO.File]::Create($tmp)
        try {
            $z = New-Object IO.Compression.GZipStream($in, [IO.Compression.CompressionMode]::Decompress)
            try { $z.CopyTo($out, 1048576) } finally { $z.Dispose() }
        }
        finally { $out.Dispose() }
    }
    finally { $in.Dispose() }

    & $mysql "--defaults-extra-file=$ConfigFile" '-e' ('CREATE DATABASE IF NOT EXISTS `{0}`' -f $TargetDatabase)
    if ($LASTEXITCODE -ne 0) { throw "Could not create database $TargetDatabase" }

    Write-Host "Loading into $TargetDatabase ..."
    $src = 'source ' + ($tmp -replace '\\', '/')
    & $mysql "--defaults-extra-file=$ConfigFile" --default-character-set=utf8mb4 "--database=$TargetDatabase" "--execute=$src"
    if ($LASTEXITCODE -ne 0) { throw "Load failed (exit $LASTEXITCODE)" }

    $count = & $mysql "--defaults-extra-file=$ConfigFile" -N -e ("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='{0}'" -f $TargetDatabase)
    Write-Host ("Restored {0} tables into {1} in {2} min" -f $count, $TargetDatabase, [math]::Round($sw.Elapsed.TotalMinutes, 1))
}
finally {
    if (Test-Path $tmp) { Remove-Item $tmp -Force }
}
