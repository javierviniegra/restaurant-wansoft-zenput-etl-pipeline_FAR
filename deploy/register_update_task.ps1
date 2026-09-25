# Registers the daily repository update as a Windows Scheduled Task.
# It must run as the Windows account that holds the GitHub credentials (Git Credential Manager is per user),
# so it asks for that account's password at registration time; the password is not stored in any script.
# Usage (elevated PowerShell): deploy\register_update_task.ps1 [-Time 00:30] [-User DOMAIN\user]
param(
    [string]$ScriptPath = (Join-Path $PSScriptRoot 'update_repo.ps1'),
    [string]$Time = '00:30',
    [string]$TaskName = 'Wansoft_Update_Repo_Diario',
    [string]$User = "$env:USERDOMAIN\$env:USERNAME"
)

$ErrorActionPreference = 'Stop'
if (-not (Test-Path $ScriptPath)) { throw "Script not found: $ScriptPath" }

$cred = Get-Credential -UserName $User -Message 'Windows password of the account that holds the GitHub credentials'
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ('-NoProfile -ExecutionPolicy Bypass -File "{0}"' -f $ScriptPath)
$trigger = New-ScheduledTaskTrigger -Daily -At $Time
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -User $cred.UserName -Password $cred.GetNetworkCredential().Password -RunLevel Highest -Force | Out-Null
Get-ScheduledTask -TaskName $TaskName | Get-ScheduledTaskInfo | Select-Object TaskName, NextRunTime
