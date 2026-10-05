from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path

from app.config import Settings
from app.models import (
    EmptyArgs,
    ExtensionInstallArgs,
    FileCopyArgs,
    FileReadArgs,
    FileWriteArgs,
    GitCloneArgs,
    PathArgs,
    ProviderConfigArgs,
    SecretSetArgs,
)
from app.paths import resolve_sandbox_path
from app.runner import CommandRunner


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, tuple[type, Callable]] = {}

    def register(self, name: str, schema: type, handler: Callable) -> None:
        self._tools[name] = (schema, handler)

    def invoke(self, name: str, arguments: dict, context: ToolContext) -> dict:
        if name not in self._tools:
            raise KeyError("Unknown tool")
        schema, handler = self._tools[name]
        args = schema.model_validate(arguments)
        return handler(context, args)

    def schemas(self) -> list[dict[str, object]]:
        return [
            {"name": name, "input_schema": schema.model_json_schema()}
            for name, (schema, _) in self._tools.items()
        ]


class ToolContext:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.runner = CommandRunner()
        self.started = time.time()
        self.owned: dict[str, subprocess.Popen] = {}

    def secret_status(self, _args: EmptyArgs) -> dict:
        names = ["GEMINI_API_KEY", "OPENROUTER_API_KEY", "GROQ_API_KEY", "OMNIROUTE_API_KEY"]
        try:
            import keyring

            stored = {
                name: bool(keyring.get_password("WindowsExecutionAgent", name)) for name in names
            }
        except Exception:
            stored = {name: False for name in names}
        return {name: "SET" if stored[name] or os.getenv(name) else "NOT_SET" for name in names}

    def secret_set(self, args: SecretSetArgs) -> dict:
        try:
            import keyring
        except ImportError as exc:
            raise RuntimeError("Install the optional keyring dependency to store secrets") from exc
        keyring.set_password("WindowsExecutionAgent", args.name, args.value)
        return {"name": args.name, "status": "SET"}

    def omniroute_status(self) -> dict:
        npm = shutil.which("npm")
        package = None
        if npm:
            try:
                result = subprocess.run(
                    [npm, "list", "-g", "omniroute", "--depth=0", "--json"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    shell=False,
                )
                package = json.loads(result.stdout).get("dependencies", {}).get("omniroute")
            except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
                package = None
        try:
            request = urllib.request.Request(self.settings.omniroute_url + "/healthz", method="GET")
            with urllib.request.urlopen(request, timeout=3) as response:
                health = response.status == 200
        except (urllib.error.URLError, TimeoutError, OSError):
            health = False
        return {
            "installed": bool(package),
            "version": package.get("version") if package else None,
            "running": health,
            "url": self.settings.omniroute_url,
        }


def build_registry() -> ToolRegistry:
    registry = ToolRegistry()

    def add(name: str, schema: type, handler: Callable) -> None:
        registry.register(name, schema, handler)

    add(
        "system.info",
        EmptyArgs,
        lambda c, a: {
            "os": platform.system(),
            "architecture": platform.machine(),
            "python": platform.python_version(),
            "git": bool(shutil.which("git")),
            "node": bool(shutil.which("node")),
            "npm": bool(shutil.which("npm")),
            "vscode": bool(shutil.which("code")),
        },
    )
    add(
        "system.disk_space",
        EmptyArgs,
        lambda c, a: {"free_bytes": shutil.disk_usage(c.settings.sandbox.parent).free},
    )
    add(
        "dependency.check",
        EmptyArgs,
        lambda c, a: {
            n: shutil.which(n) is not None for n in ("git", "node", "npm", "docker", "code")
        },
    )
    add(
        "file.exists",
        PathArgs,
        lambda c, a: {"exists": resolve_sandbox_path(c.settings.sandbox, a.path).exists()},
    )
    add(
        "file.read",
        FileReadArgs,
        lambda c, a: {
            "content": resolve_sandbox_path(c.settings.sandbox, a.path, must_exist=True).read_text(
                encoding="utf-8"
            )[: a.max_bytes]
        },
    )

    def file_write(c: ToolContext, a: FileWriteArgs) -> dict:
        path = resolve_sandbox_path(c.settings.sandbox, a.path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.is_symlink():
            raise ValueError("Symbolic links cannot be overwritten")
        path.write_text(a.content, encoding="utf-8")
        return {"written": True, "bytes": len(a.content.encode())}

    add("file.write", FileWriteArgs, file_write)
    add("file.copy", FileCopyArgs, _file_copy)
    add("file.create_directory", PathArgs, lambda c, a: _mkdir(c, a))
    add("git.status", PathArgs, lambda c, a: _git_status(c, a))
    add("git.clone", GitCloneArgs, lambda c, a: _git_clone(c, a))
    add("process.status", EmptyArgs, lambda c, a: {"owned_processes": list(c.owned.keys())})
    add("port.check", EmptyArgs, lambda c, a: _port_check(c))
    add("http.health_check", EmptyArgs, lambda c, a: c.omniroute_status())
    add("omniroute.detect", EmptyArgs, lambda c, a: _detect(c))
    add("omniroute.status", EmptyArgs, lambda c, a: c.omniroute_status())
    add("omniroute.health", EmptyArgs, lambda c, a: c.omniroute_status())
    add("omniroute.install", EmptyArgs, lambda c, a: _install_omniroute(c))
    add("omniroute.start", EmptyArgs, lambda c, a: _start_omniroute(c))
    add("omniroute.stop", EmptyArgs, lambda c, a: _stop_owned(c, "omniroute"))
    add("omniroute.restart", EmptyArgs, lambda c, a: _restart(c))
    add("omniroute.test", EmptyArgs, lambda c, a: _test_omniroute(c))
    add(
        "omniroute.configure",
        ProviderConfigArgs,
        lambda c, a: {
            "supported": False,
            "reason": (
                "OmniRoute configuration is currently done in its dashboard; "
                "agent will not invent config keys."
            ),
        },
    )
    add("secret.status", EmptyArgs, lambda c, a: c.secret_status(a))
    add("secret.set", SecretSetArgs, lambda c, a: c.secret_set(a))
    add("vscode.detect", EmptyArgs, lambda c, a: _vscode(c))
    add("vscode.version", EmptyArgs, lambda c, a: _vscode(c))
    add("vscode.extension.list", EmptyArgs, lambda c, a: _extensions(c))
    add("vscode.extension.install", ExtensionInstallArgs, lambda c, a: _extension_install(c, a))
    add("scheduler.status", EmptyArgs, lambda c, a: _scheduler(c))
    add(
        "scheduler.create",
        EmptyArgs,
        lambda c, a: {
            "created": False,
            "reason": "Use scripts/register-autostart.ps1 after reviewing its scheduled task.",
        },
    )
    add(
        "scheduler.remove",
        EmptyArgs,
        lambda c, a: {
            "removed": False,
            "reason": "Use scripts/uninstall.ps1 -RemoveAutoStart after confirmation.",
        },
    )
    return registry


def _mkdir(c: ToolContext, a: PathArgs) -> dict:
    resolve_sandbox_path(c.settings.sandbox, a.path).mkdir(parents=True, exist_ok=True)
    return {"created": True}


def _file_copy(c: ToolContext, a: FileCopyArgs) -> dict:
    source = resolve_sandbox_path(c.settings.sandbox, a.source, must_exist=True)
    destination = resolve_sandbox_path(c.settings.sandbox, a.destination)
    if destination.exists():
        raise ValueError("Destination already exists")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return {"copied": True, "bytes": destination.stat().st_size}


def _git_status(c: ToolContext, a: PathArgs) -> dict:
    path = resolve_sandbox_path(c.settings.sandbox, a.path, must_exist=True)
    if not (path / ".git").exists():
        return {"is_repository": False}
    res = c.runner.run("git", ["status", "--short", "--branch"], cwd=path)
    return {"is_repository": True, "returncode": res.returncode, "output": res.stdout}


def _git_clone(c: ToolContext, a: GitCloneArgs) -> dict:
    destination = resolve_sandbox_path(c.settings.sandbox, a.path)
    if destination.exists():
        raise ValueError("Destination already exists; inspect it before retrying")
    c.settings.sandbox.mkdir(parents=True, exist_ok=True)
    result = c.runner.run(
        "git", ["clone", "--", a.repository, str(destination)], cwd=c.settings.sandbox
    )
    return {
        "cloned": result.returncode == 0,
        "returncode": result.returncode,
        "output": result.stdout,
    }


def _detect(c: ToolContext) -> dict:
    status = c.omniroute_status()
    status["install_directory"] = str(c.settings.sandbox)
    status["git_repository"] = (c.settings.sandbox / ".git").exists()
    status["process_owned_by_agent"] = "omniroute" in c.owned
    return status


def _install_omniroute(c: ToolContext) -> dict:
    status = c.omniroute_status()
    if status["installed"]:
        return {"installed": True, "already_installed": True, "version": status["version"]}
    node = shutil.which("node")
    npm = shutil.which("npm")
    if not node or not npm:
        return {
            "installed": False,
            "reason": (
                "Install Node.js 22.22.2 or later from the official Node.js installer, then retry."
            ),
        }
    version = (
        subprocess.run([node, "--version"], capture_output=True, text=True, timeout=5, shell=False)
        .stdout.strip()
        .lstrip("v")
    )
    try:
        major, minor, patch = (int(x) for x in version.split(".")[:3])
    except (ValueError, TypeError):
        return {"installed": False, "reason": "Could not verify Node.js version."}
    if (major, minor, patch) < (22, 22, 2):
        return {"installed": False, "reason": "OmniRoute currently requires Node.js >=22.22.2."}
    c.settings.sandbox.mkdir(parents=True, exist_ok=True)
    result = c.runner.run("npm", ["install", "--global", "omniroute"], cwd=c.settings.sandbox)
    return {
        "installed": result.returncode == 0,
        "returncode": result.returncode,
        "output": result.stdout,
    }


def _start_omniroute(c: ToolContext) -> dict:
    if "omniroute" in c.owned and c.owned["omniroute"].poll() is None:
        return {"started": False, "already_running": True}
    cli = shutil.which("omniroute")
    if not cli:
        return {"started": False, "reason": "OmniRoute CLI is not installed."}
    c.settings.sandbox.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen(
        [str(Path(cli).resolve())],
        cwd=c.settings.sandbox,
        shell=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    c.owned["omniroute"] = proc
    return {"started": True, "pid": proc.pid}


def _stop_owned(c: ToolContext, name: str) -> dict:
    proc = c.owned.get(name)
    if not proc or proc.poll() is not None:
        return {"stopped": False, "reason": "No running agent-owned process."}
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
    c.owned.pop(name, None)
    return {"stopped": True}


def _restart(c: ToolContext) -> dict:
    _stop_owned(c, "omniroute")
    return _start_omniroute(c)


def _test_omniroute(c: ToolContext) -> dict:
    start = time.monotonic()
    payload = json.dumps(
        {
            "model": "auto",
            "messages": [{"role": "user", "content": "Reply with OK."}],
            "max_tokens": 8,
        }
    ).encode()
    headers = {"Content-Type": "application/json"}
    try:
        import keyring

        api_key = keyring.get_password("WindowsExecutionAgent", "OMNIROUTE_API_KEY")
    except Exception:
        api_key = None
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(
        c.settings.omniroute_url + "/v1/chat/completions",
        data=payload,
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.loads(response.read(65536))
        return {
            "success": bool(body.get("choices")),
            "model": body.get("model"),
            "latency_ms": round((time.monotonic() - start) * 1000),
        }
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        return {
            "success": False,
            "reason": "OmniRoute AI request failed or returned an invalid response.",
        }


def _port_check(c: ToolContext) -> dict:
    status = c.omniroute_status()
    return {"host": "127.0.0.1", "port": 20128, "reachable": status["running"]}


def _vscode(c: ToolContext) -> dict:
    code = shutil.which("code")
    if not code:
        return {"installed": False, "path": None, "version": None}
    result = c.runner.run("code", ["--version"])
    return {
        "installed": True,
        "path": str(Path(code).resolve()),
        "version": result.stdout.splitlines()[0] if result.stdout else "unknown",
    }


def _extensions(c: ToolContext) -> dict:
    if not shutil.which("code"):
        return {"installed": False, "extensions": []}
    result = c.runner.run("code", ["--list-extensions", "--show-versions"])
    allowed = [
        line
        for line in result.stdout.splitlines()
        if line.lower().startswith(("google.geminicodeassist@", "diegosouzapw.omnicopilot@"))
    ]
    return {"installed": True, "extensions": allowed}


def _extension_install(c: ToolContext, a: ExtensionInstallArgs) -> dict:
    if not shutil.which("code"):
        return {"installed": False, "reason": "VS Code CLI is not installed."}
    result = c.runner.run("code", ["--install-extension", a.extension_id, "--force"])
    return {
        "installed": result.returncode == 0,
        "extension_id": a.extension_id,
        "returncode": result.returncode,
    }


def _scheduler(c: ToolContext) -> dict:
    exe = shutil.which("schtasks")
    if not exe:
        return {"available": False, "task_exists": False}
    task = subprocess.run(
        [exe, "/Query", "/TN", "OmniRoute-AutoStart"],
        capture_output=True,
        text=True,
        timeout=10,
        shell=False,
    )
    return {"available": True, "task_exists": task.returncode == 0}
