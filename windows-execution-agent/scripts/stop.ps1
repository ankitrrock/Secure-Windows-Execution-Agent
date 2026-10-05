$ErrorActionPreference = 'Stop'
$Port = 8765
if ($env:AGENT_PORT) { $Port = [int]$env:AGENT_PORT }
$Connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
foreach ($Connection in $Connections) {
  $Process = Get-CimInstance Win32_Process -Filter "ProcessId=$($Connection.OwningProcess)"
  if ($Process.CommandLine -match 'uvicorn app\.main:app') { Stop-Process -Id $Connection.OwningProcess -Force }
}
Write-Output 'Windows Execution Agent stopped if it was running.'
