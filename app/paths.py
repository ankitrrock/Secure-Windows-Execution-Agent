from __future__ import annotations

from pathlib import Path


class PathDenied(ValueError):
    pass


def resolve_sandbox_path(root: Path, raw: str, *, must_exist: bool = False) -> Path:
    if not raw or "\x00" in raw or raw.startswith(("\\\\", "//")):
        raise PathDenied("Path is outside the permitted sandbox")
    candidate = Path(raw)
    if candidate.is_absolute() or candidate.drive or any(part == ".." for part in candidate.parts):
        raise PathDenied("Path is outside the permitted sandbox")
    base = root.expanduser().resolve(strict=False)
    resolved = (base / candidate).resolve(strict=must_exist)
    try:
        resolved.relative_to(base)
    except ValueError as exc:
        raise PathDenied("Path is outside the permitted sandbox") from exc
    if must_exist and not resolved.is_file():
        raise PathDenied("Only regular files are available through this tool")
    return resolved
