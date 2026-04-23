"""pytest 공통 픽스처."""

from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def _minimal_env(monkeypatch: pytest.MonkeyPatch):
    """임포트 시 선택적 시크릿 미설정으로 깨지지 않게 기본값 설정."""
    monkeypatch.setenv("OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY", "test-key-placeholder"))
    monkeypatch.setenv("APP_VERSION", "test-0.0.0")


@pytest.fixture
def mock_agent_graph(monkeypatch: pytest.MonkeyPatch):
    """LangGraph 대신 고정 AIMessage 반환."""
    from unittest.mock import MagicMock

    from langchain_core.messages import AIMessage

    mock_graph = MagicMock()

    def _invoke(payload, config=None):
        return {"messages": [AIMessage(content="테스트 답변")]}

    mock_graph.invoke.side_effect = _invoke
    import api_server

    monkeypatch.setattr(api_server, "agent_graph", mock_graph)
    return mock_graph


@pytest.fixture
def client(mock_agent_graph):
    from fastapi.testclient import TestClient

    import api_server

    return TestClient(api_server.app)
