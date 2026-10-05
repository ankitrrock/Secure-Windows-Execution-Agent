# OmniRoute operations

Target upstream: [diegosouzapw/OmniRoute](https://github.com/diegosouzapw/OmniRoute), published as the `omniroute` npm package. The upstream quick-start currently documents Node.js >=22.22.2, `npm install -g omniroute`, launch with `omniroute`, dashboard/API at port 20128, OpenAI-compatible requests at `/v1`, and a lightweight `/healthz` liveness endpoint. The agent checks the local package before installing and will not overwrite an existing installation.

## Install and run

Invoke authenticated `omniroute.detect`; then `omniroute.install` if missing. The implementation verifies Node.js version and uses only the fixed official package name. The current implementation does not install Node.js itself. `omniroute.start` starts a process only when launched by the agent; it never terminates arbitrary PIDs. Health detection probes the local service endpoint.

## Provider, models, and credentials

Use the installed OmniRoute dashboard to connect providers and review current model availability, provider terms, quotas, and pricing. The agent deliberately does not infer a free model from a stale list. Provider setup/configuration is not implemented as arbitrary JSON or environment edits. `secret.status` reveals only status; `secret.set` writes one of the allowlisted API key names to Windows Credential Manager and has no matching get operation.

## Test and IDE integration

`omniroute.test` sends `model=auto` and a short prompt to `/v1/chat/completions`, returning success, model, and latency. It does not return response contents or credentials.

For VS Code, upstream documents OmniCopilot for VS Code Copilot Chat. Google Gemini Code Assist is a separate extension and is not presumed to support arbitrary OpenAI-compatible endpoints. The agent does not modify settings files. Verify extension publisher/version and product compatibility in the Marketplace and upstream docs before using.

## Auto-start

Agent startup can be registered for the current user via `scripts/register-autostart.ps1`; this starts the agent only. Automated OmniRoute startup scheduling is not enabled by the API because process/task ownership and persistence need a separate reviewed Windows implementation. Run OmniRoute manually or use its supported service/launcher mechanisms.

## Troubleshooting

- `omniroute.install` reports missing/old Node: install a current official Node.js release with Node >=22.22.2 and reopen PowerShell.
- Health false: inspect OmniRoute's own output/dashboard and confirm port 20128 is listening on loopback.
- AI test false: connect a provider in OmniRoute, inspect provider/model status there, then retry.
- Existing app detected: no reinstall occurs; inspect before changing it.
