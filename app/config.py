from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


@dataclass(frozen=True)
class Settings:
    host: str = "127.0.0.1"
    port: int = 8765
    token_file: Path = Path.home() / "Tools" / "WindowsExecutionAgent" / "secrets" / "agent-token"
    sandbox: Path = Path.home() / "Tools" / "OmniRoute"
    audit_log: Path = Path.home() / "Tools" / "WindowsExecutionAgent" / "runtime" / "audit.jsonl"
    omniroute_url: str = "http://127.0.0.1:20128"
    request_timeout: float = 15.0
    max_request_bytes: int = 64 * 1024

    @classmethod
    def from_env(cls) -> Settings:
        host = os.getenv("AGENT_HOST", "127.0.0.1")
        if host not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("AGENT_HOST must be a loopback address")
        port = int(os.getenv("AGENT_PORT", "8765"))
        if not 1 <= port <= 65535:
            raise ValueError("AGENT_PORT must be between 1 and 65535")
        omniroute_url = os.getenv("OMNIROUTE_URL", "http://127.0.0.1:20128").rstrip("/")
        parsed_url = urlparse(omniroute_url)
        if parsed_url.scheme != "http" or parsed_url.hostname not in {
            "127.0.0.1",
            "localhost",
            "::1",
        }:
            raise ValueError("OMNIROUTE_URL must use HTTP on a loopback address")
        return cls(
            host=host,
            port=port,
            token_file=Path(
                os.path.expandvars(os.getenv("AGENT_TOKEN_FILE", str(cls.token_file)))
            ).expanduser(),
            sandbox=Path(
                os.path.expandvars(os.getenv("AGENT_SANDBOX", str(cls.sandbox)))
            ).expanduser(),
            audit_log=Path(
                os.path.expandvars(os.getenv("AGENT_AUDIT_LOG", str(cls.audit_log)))
            ).expanduser(),
            omniroute_url=omniroute_url,
        )
