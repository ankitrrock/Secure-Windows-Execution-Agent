param([switch]$SkipDependencies)
$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT') { throw 'Windows 10 or 11 is required.' }
$Root = Split-Path -Parent $PSScriptRoot
$HomeRoot = Join-Path $env:USERPROFILE 'Tools\WindowsExecutionAgent'
$Secrets = Join-Path $HomeRoot 'secrets'
$Runtime = Join-Path $HomeRoot 'runtime'
New-Item -ItemType Directory -Force -Path $Secrets,$Runtime | Out-Null
$PyLauncher = Get-Command py -ErrorAction SilentlyContinue
$Python = Get-Command python -ErrorAction SilentlyContinue
if (-not $PyLauncher -and -not $Python) { throw 'Python 3.11+ is required. Install it from python.org, then retry.' }
if (-not (Test-Path (Join-Path $Root '.venv'))) {
  if ($PyLauncher) { & $PyLauncher.Source -3 -m venv (Join-Path $Root '.venv') }
  else { & $Python.Source -m venv (Join-Path $Root '.venv') }
}
$VenvPython = Join-Path $Root '.venv\Scripts\python.exe'
if (-not $SkipDependencies) { & $VenvPython -m pip install --upgrade pip; & $VenvPython -m pip install -e "$($Root)[dev]" }
$TokenPath = Join-Path $Secrets 'agent-token'
if (-not (Test-Path $TokenPath)) {
  $Bytes = [byte[]]::new(48); [Security.Cryptography.RandomNumberGenerator]::Fill($Bytes)
  [IO.File]::WriteAllText($TokenPath, [Convert]::ToBase64String($Bytes), [Text.Encoding]::ASCII)
  $Acl = Get-Acl $TokenPath; $Acl.SetAccessRuleProtection($true,$false)
  $Rule = [Security.AccessControl.FileSystemAccessRule]::new($env:USERNAME,'FullControl','Allow')
  $Acl.SetAccessRule($Rule); Set-Acl -Path $TokenPath -AclObject $Acl
}
Write-Output 'Installation complete. Token generated and stored with user-only ACL; value is not displayed.'
Write-Output "Start with: & '$PSScriptRoot\start.ps1'"
