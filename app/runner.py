from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


class CommandRunner:
    """Internal structured process runner. No API accepts executable paths or command strings."""

    def __init__(self, timeout: float = 120.0) -> None:
        self.timeout = timeout

    def resolve(self, executable: str) -> str:
        if executable not in {"git", "node", "npm", "code", "schtasks"}:
            raise PermissionError("Executable is not approved")
        path = shutil.which(executable)
        if not path:
            raise FileNotFoundError(f"{executable} is not installed")
        return str(Path(path).resolve())

    def run(self, executable: str, args: list[str], cwd: Path | None = None) -> CommandResult:
        exe = self.resolve(executable)
        if any(not isinstance(arg, str) or "\x00" in arg for arg in args):
            raise ValueError("Invalid argument")
        completed = subprocess.run(
            [exe, *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=self.timeout,
            shell=False,
            env={
                "PATH": os.environ.get("PATH", ""),
                "SystemRoot": os.environ.get("SystemRoot", ""),
            },
        )
        from app.redaction import redact

        return CommandResult(
            completed.returncode, redact(completed.stdout[-8192:]), redact(completed.stderr[-8192:])
        )
