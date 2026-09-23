# Weekly MySQL/MariaDB backup: one gzip'd dump per database, keeps the newest $Keep successful runs.
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File backup_mysql.ps1
param(
    [string]$BackupRoot = 'C:\Backups\mysql',
    [string]$ConfigFile = 'C:\Backups\mysql\backup.cnf',
    [string[]]$Databases = @('wansoft', 'zenput', 'odoo', 'presupuestos_ap'),
    [string]$MysqlBin = '',
    [int]$Keep = 2,
    [int]$MinFreeGB = 80
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression

$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$runDir = Join-Path $BackupRoot $stamp
$logFile = Join-Path $BackupRoot 'backup.log'
New-Item -ItemType Directory -Force $BackupRoot | Out-Null

function Write-Log([string]$msg) {
    $line = '{0} {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $msg
    Write-Host $line
    Add-Content -Path $logFile -Value $line
}

function Find-MysqlDump {
    $candidates = @()
    if ($MysqlBin) { $candidates += Join-Path $MysqlBin 'mysqldump.exe' }
    $candidates += 'C:\xampp\mysql\bin\mysqldump.exe'
    $proc = Get-Process mysqld, mariadbd -ErrorAction SilentlyContinue | Where-Object { $_.Path } | Select-Object -First 1
    if ($proc) { $candidates += Join-Path (Split-Path $proc.Path) 'mysqldump.exe' }
    $cmd = Get-Command mysqldump.exe -ErrorAction SilentlyContinue
    if ($cmd) { $candidates += $cmd.Source }
    foreach ($c in $candidates) { if (Test-Path $c) { return $c } }
    throw 'mysqldump.exe not found. Pass -MysqlBin with the folder that contains it.'
}

function Test-DumpComplete([string]$path) {
    $fs = [IO.File]::OpenRead($path)
    try {
        $len = [int][Math]::Min(512, $fs.Length)
        [void]$fs.Seek(-$len, [IO.SeekOrigin]::End)
        $buf = New-Object byte[] $len
        [void]$fs.Read($buf, 0, $len)
        return ([Text.Encoding]::ASCII.GetString($buf) -match 'Dump completed')
    }
    finally { $fs.Dispose() }
}

function Compress-FileGz([string]$src, [string]$dst) {
    $in = [IO.File]::OpenRead($src)
    try {
        $out = [IO.File]::Create($dst)
        try {
            $gz = New-Object IO.Compression.GZipStream($out, [IO.Compression.CompressionLevel]::Fastest)
            try { $in.CopyTo($gz, 1048576) } finally { $gz.Dispose() }
        }
        finally { $out.Dispose() }
    }
    finally { $in.Dispose() }
}

function Test-Gz([string]$path) {
    $in = [IO.File]::OpenRead($path)
    try {
        $gz = New-Object IO.Compression.GZipStream($in, [IO.Compression.CompressionMode]::Decompress)
        try {
            $buf = New-Object byte[] 4194304
            while ($gz.Read($buf, 0, $buf.Length) -gt 0) { }
        }
        finally { $gz.Dispose() }
    }
    finally { $in.Dispose() }
}

$failed = $false
try {
    if (-not (Test-Path $ConfigFile)) { throw "Config file not found: $ConfigFile" }
    $mysqldump = Find-MysqlDump

    Get-ChildItem $BackupRoot -Directory |
        Where-Object { $_.Name -match '^\d{8}_\d{6}$' -and -not (Test-Path (Join-Path $_.FullName 'OK.txt')) } |
        ForEach-Object { Write-Log "Removing partial run $($_.Name)"; Remove-Item $_.FullName -Recurse -Force }

    $drive = (Split-Path $BackupRoot -Qualifier).TrimEnd(':')
    $free = [math]::Round((Get-PSDrive -Name $drive).Free / 1GB, 1)
    if ($free -lt $MinFreeGB) { throw "Only $free GB free on $drive, need at least $MinFreeGB GB" }

    New-Item -ItemType Directory -Force $runDir | Out-Null
    Write-Log "Backup started -> $runDir (free space $free GB)"
    $summary = @()
    foreach ($db in $Databases) {
        $sw = [Diagnostics.Stopwatch]::StartNew()
        $sql = Join-Path $runDir "$db.sql"
        $gz = "$sql.gz"
        & $mysqldump "--defaults-extra-file=$ConfigFile" --single-transaction --quick --routines --triggers --events --hex-blob --default-character-set=utf8mb4 "--result-file=$sql" $db
        if ($LASTEXITCODE -ne 0) { throw "mysqldump failed for $db (exit $LASTEXITCODE)" }
        if (-not (Test-DumpComplete $sql)) { throw "Dump of $db is incomplete (no completion marker)" }
        Compress-FileGz $sql $gz
        Remove-Item $sql -Force
        Test-Gz $gz
        $mb = [math]::Round((Get-Item $gz).Length / 1MB, 1)
        Write-Log ("{0} OK: {1} MB in {2} min" -f $db, $mb, [math]::Round($sw.Elapsed.TotalMinutes, 1))
        $summary += "$db $mb MB"
    }
    Set-Content (Join-Path $runDir 'OK.txt') ("Completed " + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + "`r`n" + ($summary -join "`r`n"))

    $done = @(Get-ChildItem $BackupRoot -Directory |
        Where-Object { $_.Name -match '^\d{8}_\d{6}$' -and (Test-Path (Join-Path $_.FullName 'OK.txt')) } |
        Sort-Object Name -Descending)
    $done | Select-Object -Skip $Keep | ForEach-Object { Write-Log "Pruning old backup $($_.Name)"; Remove-Item $_.FullName -Recurse -Force }
    Write-Log ("Backup finished. Kept: " + ((@($done | Select-Object -First $Keep) | ForEach-Object { $_.Name }) -join ', '))
}
catch {
    $failed = $true
    Write-Log "BACKUP FAILED: $($_.Exception.Message)"
    if (Test-Path $runDir) { Remove-Item $runDir -Recurse -Force -ErrorAction SilentlyContinue }
}
if ($failed) { exit 1 }
