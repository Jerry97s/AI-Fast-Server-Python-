from __future__ import annotations


def test_ready_schema(client):
    r = client.get("/ready")
    assert r.status_code in (200, 503)
    data = r.json()
    assert "ready" in data
    assert "checks" in data
    assert "version" in data
    assert isinstance(data["checks"], dict)
