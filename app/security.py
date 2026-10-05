from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
from collections import defaultdict, deque
from pathlib import Path

from app.redaction import redact


def generate_token(path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    token = secrets.token_urlsafe(48)
    flags = "x" if not path.exists() else "w"
    with path.open(flags, encoding="utf-8") as stream:
        stream.write(token)
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return token


def verify_token(provided: str | None, expected: str) -> bool:
    return bool(provided) and hmac.compare_digest(
        hashlib.sha256(provided.encode()).digest(), hashlib.sha256(expected.encode()).digest()
    )


class RateLimiter:
    def __init__(self, limit: int = 60, window_seconds: int = 60) -> None:
        self.limit, self.window_seconds = limit, window_seconds
        self._requests: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        bucket = self._requests[key]
        while bucket and now - bucket[0] >= self.window_seconds:
            bucket.popleft()
        if len(bucket) >= self.limit:
            return False
        bucket.append(now)
        return True


def audit(path: Path, event: str, outcome: str, request_id: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "time": time.time(),
        "event": redact(event),
        "outcome": outcome,
        "request_id": request_id,
    }
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=True) + "\n")
    try:
        path.chmod(0o600)
    except OSError:
        pass
