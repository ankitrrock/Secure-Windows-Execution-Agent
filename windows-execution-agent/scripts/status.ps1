$Port = 8765
if ($env:AGENT_PORT) { $Port = [int]$env:AGENT_PORT }
$Listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
$Health = $null
$TokenPath = Join-Path $env:USERPROFILE 'Tools\WindowsExecutionAgent\secrets\agent-token'
try {
  $Token = Get-Content -Raw -LiteralPath $TokenPath
  $Health = (Invoke-RestMethod "http://127.0.0.1:$Port/health" -Headers @{ Authorization = "Bearer $Token" } -TimeoutSec 2).status
} catch { $Health = 'unavailable' }
finally { $Token = $null }
[pscustomobject]@{ Agent = $Health; Port = $Port; PID = $Listener.OwningProcess; OmniRoute = 'See authenticated /status'; VSCode = [bool](Get-Command code -ErrorAction SilentlyContinue) }
