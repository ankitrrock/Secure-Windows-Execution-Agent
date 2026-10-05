# n8n integration

## Start and authenticate

Start the service on the Windows machine with `scripts/start.ps1`. It binds to `127.0.0.1:8765`. Every API endpoint requires `Authorization: Bearer <token>`.

Provision the token from `%USERPROFILE%\Tools\WindowsExecutionAgent\secrets\agent-token` into an n8n HTTP Header Auth credential. Do not include it in prompts, workflow expressions visible to the AI, node output, or execution logs. Use the HTTP Request node with credential attachment and JSON body.

## Calling a tool

`POST http://127.0.0.1:8765/tools/call`

```json
{"name":"system.info","arguments":{}}
```

Example response:

```json
{"success":true,"tool":"system.info","result":{"os":"Windows","architecture":"AMD64","python":"3.x","git":true,"node":true,"npm":true,"vscode":false},"request_id":"..."}
```

Get discoverable strict schemas from authenticated `GET /tools`. Reject/handle HTTP 401 (credential), 413 (body too large), 422 (schema), 429 (rate limit), 404 (unknown tool), and 400 (operation failed). Error responses do not echo inputs.

## Suggested workflow

Chat/Webhook Trigger → AI Agent with a tool wrapper restricted to `POST /tools/call` → `system.info` → `dependency.check` → `omniroute.detect` → if absent, request explicit approval before `omniroute.install` → ask the user to configure a provider in OmniRoute dashboard if needed → `omniroute.start` → `omniroute.health` → `omniroute.test` → `vscode.detect` → `vscode.extension.list` → install an allowlisted extension only with user intent → verify extension list → optionally register the Windows agent auto-start through its reviewed script.

Do not give the AI a shell node, arbitrary URL node, or generic command execution tool. Do not treat a model-generated tool name as authorization; server registry and schemas are authoritative. OmniRoute installation requires npm network access and executes the official package installer under the user account.

## Remote n8n

`127.0.0.1` is only reachable from the same machine. For remote n8n, connect through a private VPN, private network, or authenticated outbound tunnel/relay with device identity and narrow access policy. Keep the agent bound to loopback, and do not expose port 8765 through router/firewall port forwarding or an unauthenticated public tunnel.

## Tools

Request schemas are discoverable via `/tools`. Every tool has an `arguments` object; no tool accepts a command string. `secret.status` returns only SET/NOT_SET. `secret.set` accepts a strict secret name and value; route that value directly from a protected credential field and disable n8n node output retention for the request. Avoid placing it in AI input or execution logs.
