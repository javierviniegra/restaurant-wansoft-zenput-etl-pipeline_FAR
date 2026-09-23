# Registers the weekly backup as a Windows Scheduled Task (runs as SYSTEM, Sundays by default).
# Usage (elevated PowerShell): register_backup_task.ps1 [-ScriptPath C:\Backups\scripts\backup_mysql.ps1] [-Time 07:30]
param(
    [string]$ScriptPath = 'C:\Backups\scripts\backup_mysql.ps1',
    [string]$Time = '07:30',
    [string]$TaskName = 'Wansoft_Backup_MySQL_Semanal'
)

$ErrorActionPreference = 'Stop'
if (-not (Test-Path $ScriptPath)) { throw "Script not found: $ScriptPath" }

$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ('-NoProfile -ExecutionPolicy Bypass -File "{0}"' -f $ScriptPath)
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At $Time
$principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 8)
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
Get-ScheduledTask -TaskName $TaskName | Get-ScheduledTaskInfo | Select-Object TaskName, NextRunTime
