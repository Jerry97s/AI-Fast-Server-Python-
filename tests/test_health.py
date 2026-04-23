from __future__ import annotations


def test_health_returns_version_and_model(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "model" in data
    assert isinstance(data["model"], str)
    assert len(data["model"]) > 0
