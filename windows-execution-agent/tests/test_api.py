from dataclasses import replace

from fastapi.testclient import TestClient

from app import main


def test_health_requires_authentication(monkeypatch) -> None:
    monkeypatch.setattr(main, "load_token", lambda: "correct-token")
    client = TestClient(main.app)
    assert client.get("/health").status_code == 401
    response = client.get("/health", headers={"Authorization": "Bearer correct-token"})
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_api_requires_authentication(monkeypatch) -> None:
    monkeypatch.setattr(main, "load_token", lambda: "correct-token")
    client = TestClient(main.app)
    assert client.get("/tools").status_code == 401
    assert client.get("/tools", headers={"Authorization": "Bearer wrong-token"}).status_code == 401
    assert (
        client.get("/tools", headers={"Authorization": "Bearer correct-token"}).status_code == 200
    )


def test_unknown_tool_rejected(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(main, "load_token", lambda: "correct-token")
    monkeypatch.setattr(
        main, "settings", replace(main.settings, audit_log=tmp_path / "audit.jsonl")
    )
    client = TestClient(main.app)
    response = client.post(
        "/tools/call",
        headers={"Authorization": "Bearer correct-token"},
        json={"name": "does.not.exist", "arguments": {}},
    )
    assert response.status_code == 404
