# Registers the morning cash-closing pass (owner, 2026-10-12): Wansoft_Cortes_Manana, daily at 07:30.
# Some branches (Antenas, Coyoacán, Taquería Parroquia, Versalles, Vía Vallejo...) upload their
# Wansoft cash closing to the cloud after the 01:30 cycle has run, so it reached the warehouse a
# night late; Central de Reportes reads at 08:00. This pass re-runs only the stage
# "Costos - cierre global de caja" (same 5-day window, upsert by subsidiary_id + fecha_corte,
# about 25 s) and logs to logs\cash_closing_morning_<yyyyMMdd>.log.
# Runs as the given Windows account (asks for its password; the password is not stored in any script).
# Usage (elevated PowerShell, on the tasks VM): deploy\register_cash_closing_task.ps1 [-Time 07:30] [-User DOMAIN\user]
param(
    [string]$ScriptPath = (Join-Path $PSScriptRoot 'run_daily_cycle.ps1'),
    [string]$Time = '07:30',
    [string]$TaskName = 'Wansoft_Cortes_Manana',
    [string]$User = "$env:USERDOMAIN\$env:USERNAME"
)

$ErrorActionPreference = 'Stop'
if (-not (Test-Path $ScriptPath)) { throw "Script not found: $ScriptPath" }

$cred = Get-Credential -UserName $User -Message 'Windows password of the account that runs the pipeline'
$arguments = '-NoProfile -ExecutionPolicy Bypass -File "{0}" -Only "cierre global" -LogPrefix cash_closing_morning' -f $ScriptPath
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arguments
$trigger = New-ScheduledTaskTrigger -Daily -At $Time
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -User $cred.UserName -Password $cred.GetNetworkCredential().Password -RunLevel Highest -Force | Out-Null
Get-ScheduledTask -TaskName $TaskName | Get-ScheduledTaskInfo | Select-Object TaskName, NextRunTime
