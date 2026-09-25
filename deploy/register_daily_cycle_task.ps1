# Registers the daily pipeline cycle as a Windows Scheduled Task, DISABLED unless -Enable is passed.
# Enable it only at go-live: before that the legacy tasks still write to the same production database.
# Runs as the given Windows account (asks for its password; the password is not stored in any script).
# Usage (elevated PowerShell): deploy\register_daily_cycle_task.ps1 [-Enable] [-Time 01:00] [-User DOMAIN\user]
param(
    [string]$ScriptPath = (Join-Path $PSScriptRoot 'run_daily_cycle.ps1'),
    [string]$Time = '01:00',
    [string]$TaskName = 'Wansoft_Pipeline_Diario',
    [string]$User = "$env:USERDOMAIN\$env:USERNAME",
    [switch]$Enable
)

$ErrorActionPreference = 'Stop'
if (-not (Test-Path $ScriptPath)) { throw "Script not found: $ScriptPath" }

$cred = Get-Credential -UserName $User -Message 'Windows password of the account that will run the daily pipeline'
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ('-NoProfile -ExecutionPolicy Bypass -File "{0}"' -f $ScriptPath)
$trigger = New-ScheduledTaskTrigger -Daily -At $Time
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 4)
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -User $cred.UserName -Password $cred.GetNetworkCredential().Password -RunLevel Highest -Force | Out-Null
if (-not $Enable) { Disable-ScheduledTask -TaskName $TaskName | Out-Null }
Get-ScheduledTask -TaskName $TaskName | Select-Object TaskName, State
