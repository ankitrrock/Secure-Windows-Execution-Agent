# Installation

Requirements: Windows 10/11, Python 3.11 or newer, and access to install Python packages. OmniRoute requires Node.js >=22.22.2 only when that tool is used.

In PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\install.ps1
.\scripts\start.ps1
```

The installer creates a virtual environment, installs app/development dependencies, generates a high-entropy bearer token without printing it, and stores that token outside the repository. Confirm `/health` at `http://127.0.0.1:8765/health` using the bearer token. For n8n, securely provision the token as an HTTP Header Auth credential (details in `N8N_INTEGRATION.md`).

Management scripts are in `scripts/`. No administrator elevation is required. This project build does not install OmniRoute or VS Code.
