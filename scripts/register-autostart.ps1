param([switch]$Remove)
$ErrorActionPreference = 'Stop'
$Name = 'WindowsExecutionAgent-AutoStart'
$Existing = Get-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue
if ($Remove) {
  if ($Existing) { Unregister-ScheduledTask -TaskName $Name -Confirm:$false }
  Write-Output 'Auto-start task removed if present.'; exit 0
}
if ($Existing) { Write-Output 'Auto-start task already exists; no duplicate created.'; exit 0 }
$Action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -WindowStyle Hidden -File `"$PSScriptRoot\start.ps1`"" -WorkingDirectory (Split-Path -Parent $PSScriptRoot)
$Trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Days 0)
Register-ScheduledTask -TaskName $Name -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings -Description 'Start the authenticated local Windows Execution Agent.' | Out-Null
Write-Output 'Auto-start registered for current user.'
