param([switch]$RemoveAutoStart)
& "$PSScriptRoot\stop.ps1"
if ($RemoveAutoStart) { & "$PSScriptRoot\register-autostart.ps1" -Remove }
Write-Output 'Agent stopped. Project, logs, secrets, and OmniRoute user data were preserved.'
