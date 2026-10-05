from __future__ import annotations

import re

_PATTERNS = [
    re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)[^\s,;]+"),
    re.compile(r"(?i)(\bbearer\s+)[A-Za-z0-9._~+/=-]{8,}"),
    re.compile(r"(?i)(\b(?:api[_-]?key|password|passwd|token|secret|cookie)\b\s*[:=]\s*)[^\s,;]+"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)(://[^:/\s]+:)[^@/\s]+(@)"),
]


def redact(value: str) -> str:
    result = value
    for pattern in _PATTERNS:
        if pattern.groups >= 2:
            result = pattern.sub(r"\1[REDACTED]\2", result)
        elif pattern.groups == 1:
            result = pattern.sub(r"\1[REDACTED]", result)
        else:
            result = pattern.sub("[REDACTED]", result)
    return result
