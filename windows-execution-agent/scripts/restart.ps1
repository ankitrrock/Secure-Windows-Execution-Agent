$ErrorActionPreference = 'Stop'
& "$PSScriptRoot\stop.ps1"
Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',"$PSScriptRoot\start.ps1") -WindowStyle Hidden
Start-Sleep -Seconds 2
$TokenPath = Join-Path $env:USERPROFILE 'Tools\WindowsExecutionAgent\secrets\agent-token'
$Token = Get-Content -Raw -LiteralPath $TokenPath
$Port = 8765
if ($env:AGENT_PORT) { $Port = [int]$env:AGENT_PORT }
try { Invoke-RestMethod "http://127.0.0.1:$Port/health" -Headers @{ Authorization = "Bearer $Token" } -TimeoutSec 4 | Out-Null }
catch { throw 'Agent did not become healthy.' }
finally { $Token = $null }
Write-Output 'Agent restarted and authenticated health check passed.'
