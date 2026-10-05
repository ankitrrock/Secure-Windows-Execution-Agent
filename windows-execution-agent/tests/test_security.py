from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import Settings
from app.paths import PathDenied, resolve_sandbox_path
from app.redaction import redact
from app.security import RateLimiter, verify_token
from app.tools import ToolContext, build_registry


def test_path_sandbox_allows_relative_and_rejects_escape(tmp_path: Path) -> None:
    root = tmp_path / "safe"
    root.mkdir()
    assert resolve_sandbox_path(root, "config/settings.json").is_relative_to(root)
    for unsafe in (
        "../secret.txt",
        "..\\secret.txt",
        "C:\\Windows\\win.ini",
        "\\\\host\\share\\x",
        "/etc/passwd",
    ):
        with pytest.raises(PathDenied):
            resolve_sandbox_path(root, unsafe)


def test_symlink_escape_is_rejected(tmp_path: Path) -> None:
    root, outside = tmp_path / "safe", tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (outside / "secret.txt").write_text("private")
    try:
        (root / "link").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("Symlink creation is unavailable")
    with pytest.raises(PathDenied):
        resolve_sandbox_path(root, "link/secret.txt", must_exist=True)


def test_auth_token_constant_time_semantics() -> None:
    assert verify_token("strong-token", "strong-token")
    assert not verify_token("wrong-token", "strong-token")
    assert not verify_token(None, "strong-token")


def test_redaction_covers_headers_password_and_connection_strings() -> None:
    value = "Authorization: Bearer abcdefghijkl password=hunter2 https://user:pass@example.test"
    result = redact(value)
    assert "abcdefghijkl" not in result
    assert "hunter2" not in result
    assert "user:pass" not in result


def test_rate_limit() -> None:
    limiter = RateLimiter(limit=2, window_seconds=60)
    assert limiter.allow("127.0.0.1")
    assert limiter.allow("127.0.0.1")
    assert not limiter.allow("127.0.0.1")


def test_registry_denies_unknown_and_arbitrary_secret_read(tmp_path: Path) -> None:
    registry = build_registry()
    context = ToolContext(Settings(sandbox=tmp_path))
    with pytest.raises(KeyError):
        registry.invoke("secret.get", {}, context)
    with pytest.raises(KeyError):
        registry.invoke("powershell", {"command": "echo harmless"}, context)


def test_tool_schema_rejects_extra_fields(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        build_registry().invoke(
            "omniroute.start", {"command": "whoami"}, ToolContext(Settings(sandbox=tmp_path))
        )


def test_runner_allowlist() -> None:
    from app.runner import CommandRunner

    with pytest.raises(PermissionError):
        CommandRunner().resolve("powershell")
