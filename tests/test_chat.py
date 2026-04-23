from __future__ import annotations


def test_chat_success_schema(client):
    r = client.post(
        "/v1/chat",
        json={"message": "안녕", "thread_id": "t1"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["reply"] == "테스트 답변"
    assert data["thread_id"] == "t1"


def test_chat_legacy_alias(client):
    r = client.post("/chat", json={"message": "hello", "thread_id": "t2"})
    assert r.status_code == 200
    assert r.json()["thread_id"] == "t2"


def test_chat_validation_empty_message(client):
    r = client.post("/v1/chat", json={"message": ""})
    assert r.status_code == 422
    body = r.json()
    assert "error" in body
    assert body["error"]["code"] == "validation_error"


def test_chat_agent_error_json_shape(client, monkeypatch):
    import api_server

    def boom(*a, **k):
        raise TimeoutError("forced")

    monkeypatch.setattr(api_server.agent_graph, "invoke", boom)

    r = client.post("/v1/chat", json={"message": "test"})
    assert r.status_code == 504
    body = r.json()
    assert body["error"]["code"] == "model_timeout"
    assert "request_id" in body
