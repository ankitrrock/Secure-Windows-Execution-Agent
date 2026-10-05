$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$env:AGENT_TOKEN_FILE = Join-Path $env:USERPROFILE 'Tools\WindowsExecutionAgent\secrets\agent-token'
$env:AGENT_AUDIT_LOG = Join-Path $env:USERPROFILE 'Tools\WindowsExecutionAgent\runtime\audit.jsonl'
$env:AGENT_SANDBOX = Join-Path $env:USERPROFILE 'Tools\OmniRoute'
$Port = 8765
if ($env:AGENT_PORT) { $Port = [int]$env:AGENT_PORT }
& (Join-Path $Root '.venv\Scripts\python.exe') -m uvicorn app.main:app --host 127.0.0.1 --port $Port
