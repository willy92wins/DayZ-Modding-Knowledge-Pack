# Run inside the VM as Administrator, from the folder that holds this file + config.json.
#   powershell -ExecutionPolicy Bypass -File .\install.ps1            install / update
#   powershell -ExecutionPolicy Bypass -File .\install.ps1 -Uninstall
#   powershell -ExecutionPolicy Bypass -File .\install.ps1 -DayZFirewall   also open DayZ server ports
param([switch]$Uninstall, [switch]$DayZFirewall)
$ErrorActionPreference = 'Stop'
$dir = 'C:\ovh-agent'; $task = 'OVH-IdleShelve'
if ($Uninstall) {
  Unregister-ScheduledTask -TaskName $task -Confirm:$false -ErrorAction SilentlyContinue
  Write-Host "task removed ($dir kept: delete it by hand, it holds the API key)"; exit 0
}
New-Item -ItemType Directory -Force $dir | Out-Null
Copy-Item "$PSScriptRoot\ovh-idle-shelve.ps1", "$PSScriptRoot\config.json" $dir -Force
# config.json holds API secrets: SYSTEM + Administrators only
icacls $dir /inheritance:r /grant:r 'SYSTEM:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' | Out-Null

$act = New-ScheduledTaskAction -Execute 'powershell.exe' `
  -Argument "-NoProfile -ExecutionPolicy Bypass -File $dir\ovh-idle-shelve.ps1"
$t1 = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 5)
$t2 = New-ScheduledTaskTrigger -AtStartup
$set = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 4) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $task -Action $act -Trigger $t1,$t2 -Settings $set -User 'SYSTEM' -RunLevel Highest -Force | Out-Null
Write-Host "installed $task (every 5 min). Dry run now:"
& powershell -NoProfile -ExecutionPolicy Bypass -File "$dir\ovh-idle-shelve.ps1" -DryRun
Get-Content "$dir\agent.log" -Tail 1

if ($DayZFirewall) {
  New-NetFirewallRule -DisplayName 'DayZ Server UDP' -Direction Inbound -Protocol UDP -LocalPort 2302-2306,27016 -Action Allow -ErrorAction SilentlyContinue | Out-Null
  Write-Host 'opened UDP 2302-2306, 27016'
}
