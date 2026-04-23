"""
환경 변수 기반 설정 (비밀은 코드에 넣지 않음).

프로덕션: `.env` 또는 OS 환경 변수로 주입.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


def _project_root() -> Path:
    return Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_project_root() / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(default="ai-agent-py", validation_alias="APP_NAME")
    app_version: str = Field(default="0.1.0", validation_alias="APP_VERSION")

    # LLM (OpenAI 호환 API: OpenAI / Azure 호환 게이트웨이 / 일부 로컬 프록시)
    openai_api_key: SecretStr | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    agent_model: str = Field(default="gpt-4o-mini", validation_alias="AGENT_MODEL")
    agent_llm_temperature: float = Field(default=0.7, validation_alias="AGENT_LLM_TEMPERATURE")
    agent_llm_timeout_seconds: float = Field(default=120.0, validation_alias="AGENT_LLM_TIMEOUT_SECONDS")
    agent_llm_max_tokens: int | None = Field(default=None, validation_alias="AGENT_LLM_MAX_TOKENS")
    openai_api_base: str | None = Field(default=None, validation_alias="OPENAI_API_BASE")

    # HTTP 서버 기본값 (프로덕션은 로컬만 리슨 권장)
    agent_api_host: str = Field(default="127.0.0.1", validation_alias="AGENT_API_HOST")
    agent_api_port: int = Field(default=8787, validation_alias="AGENT_API_PORT")

    # 운영
    agent_rate_limit_per_minute: int = Field(default=120, validation_alias="AGENT_RATE_LIMIT_PER_MINUTE")
    agent_log_message_preview_chars: int = Field(
        default=120, validation_alias="AGENT_LOG_MESSAGE_PREVIEW_CHARS"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


def mask_preview(text: str | None, max_chars: int | None = None) -> str:
    if not text:
        return ""
    s = get_settings()
    n = max_chars if max_chars is not None else s.agent_log_message_preview_chars
    t = text.replace("\r", " ").replace("\n", " ")
    if len(t) <= n:
        return t
    return t[:n] + "…"

