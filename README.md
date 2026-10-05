# Secure Windows Execution Agent

An authenticated, local-only FastAPI service that exposes narrowly typed Windows operations to n8n. It is designed to avoid arbitrary shell, PowerShell, CMD, or Python execution. The project runs on Windows 10/11 with Python 3.11+.

## Install and run

Open PowerShell in this directory:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\install.ps1
.\scripts\start.ps1
```

The listener is bound to `127.0.0.1:8765`; all API routes, including `GET /health`, require a bearer token stored at `%USERPROFILE%\Tools\WindowsExecutionAgent\secrets\agent-token`. The installer never prints it. Read it only to provision an n8n credential, using a secure local credential workflow. `/docs` describes schemas; API operations are authenticated. Never put the token in an AI prompt.

## Security design

The tool registry defines every available operation and its strict Pydantic schema. Unknown tools and extra fields fail closed. Command execution is internal and structured with `shell=False`, a fixed executable allowlist, timeouts, and bounded/redacted output. File operations are constrained to `%USERPROFILE%\Tools\OmniRoute`; path traversal, absolute paths, UNC paths, and resolved symlink escapes are denied. Secrets can be written to Windows Credential Manager via `secret.set`; no API reads them back. Logs contain operation names and outcomes, not request bodies. Rate limiting and request size checks apply to the API.

Security limits: this runs with the logged-in Windows user's permissions. Local malware with the same account can access user-readable files. The audit log is local and not tamper-proof. Rate limits are in-memory and process-local. The HTTP API has no TLS because it listens only on loopback. Remote n8n needs a private VPN or authenticated outbound tunnel; do not expose this port publicly.

## Available tools

`system.info`, `system.disk_space`, `dependency.check`, `file.exists`, `file.read`, `file.write`, `file.create_directory`, `git.status`, `git.clone`, `process.status`, `port.check`, `http.health_check`, `omniroute.detect/install/configure/start/stop/restart/status/health/test`, `secret.status`, `secret.set`, `vscode.detect/version/extension.list/extension.install`, `scheduler.status/create/remove`.

Some conservative operations report an explicit unsupported result. This build does not install VS Code, mutate its settings, or create scheduler tasks through the AI API. Use the supplied reviewed scripts for agent auto-start. OmniRoute provider setup is performed through its own dashboard; no secret read or provider-specific configuration endpoint is exposed here.

## OmniRoute

The agent targets the official [diegosouzapw/OmniRoute](https://github.com/diegosouzapw/OmniRoute) repository and `omniroute` npm package. Current upstream install notes list Node.js >=22.22.2, `npm install -g omniroute`, default port 20128, and an OpenAI-compatible `/v1/chat/completions` API. The agent checks installation first, validates Node version, then installs the official package. It will not select or claim a model is free; use OmniRoute's own current dashboard and provider terms. A minimal smoke test sends a short prompt to model `auto` and returns only success/model/latency.

## VS Code

The extension allowlist includes Google's official `Google.geminicodeassist` and upstream OmniRoute's `diegosouzapw.omnicopilot`. They are separate products. Gemini Code Assist does not become an OmniRoute client by installing it. OmniCopilot is the documented OmniRoute integration for the VS Code Copilot Chat model picker (with compatible VS Code/Copilot Chat versions); actual extension availability should be verified in VS Code before relying on it. No settings file is edited.

## API and n8n

See [N8N_INTEGRATION.md](N8N_INTEGRATION.md) for authentication, schemas, workflow outline, and remote connectivity. API routes: `GET /health`, authenticated `GET /status`, `GET /tools`, and `POST /tools/call` with `{ "name": "system.info", "arguments": {} }`.

## Commands

```powershell
.\scripts\install.ps1
.\scripts\start.ps1
.\scripts\stop.ps1
.\scripts\restart.ps1
.\scripts\status.ps1
Invoke-RestMethod http://127.0.0.1:8765/health
.\.venv\Scripts\python.exe -m pytest
.\scripts\register-autostart.ps1
.\scripts\register-autostart.ps1 -Remove
```

## Limitations and troubleshooting

No actual OmniRoute installation or cloud-provider credential setup is performed during this project build. Install/setup network calls occur only when an authenticated tool is explicitly invoked. If Node is missing or below the verified minimum, install current Node.js from [nodejs.org](https://nodejs.org/), then retry `omniroute.install`. If API calls return 401, provision the generated token as an n8n credential and restart after changing token storage. Review `runtime/audit.jsonl` for operation outcomes; it excludes payloads.
