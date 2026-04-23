"""
환경 변수 기반 설정 (비밀은 코드에 넣지 않음).

프로덕션: `.env` 또는 OS 환경 변수로 주입.
"""

from __future__ import annotations

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
    agent_llm_timeout_seconds: float = Field(
        default=120.0, validation_alias="AGENT_LLM_TIMEOUT_SECONDS"
    )
    agent_llm_max_tokens: int | None = Field(default=None, validation_alias="AGENT_LLM_MAX_TOKENS")
    openai_api_base: str | None = Field(default=None, validation_alias="OPENAI_API_BASE")

    # HTTP 서버 기본값 (프로덕션은 로컬만 리슨 권장)
    agent_api_host: str = Field(default="127.0.0.1", validation_alias="AGENT_API_HOST")
    agent_api_port: int = Field(default=8787, validation_alias="AGENT_API_PORT")

    # HTTP — CORS (프로덕션에서는 특정 출처만 나열 권장; 와일드카드는 개발 편의용)
    agent_cors_origins: str = Field(default="*", validation_alias="AGENT_CORS_ORIGINS")

    # 선택: 원격 노출 시 역프록시 뒤에서 Bearer로 API 보호 (비우면 비활성)
    agent_api_bearer_token: SecretStr | None = Field(
        default=None, validation_alias="AGENT_API_BEARER_TOKEN"
    )

    # 운영
    agent_rate_limit_per_minute: int = Field(
        default=120, validation_alias="AGENT_RATE_LIMIT_PER_MINUTE"
    )
    agent_log_message_preview_chars: int = Field(
        default=120, validation_alias="AGENT_LOG_MESSAGE_PREVIEW_CHARS"
    )
    agent_log_max_bytes: int = Field(
        default=5_242_880, validation_alias="AGENT_LOG_MAX_BYTES"
    )  # 5 MiB
    agent_log_backup_count: int = Field(default=3, validation_alias="AGENT_LOG_BACKUP_COUNT")

    # 장기 메모리 JSON — history 배열 상한 (초과 시 오래된 항목 제거)
    agent_memory_history_max_items: int = Field(
        default=500, validation_alias="AGENT_MEMORY_HISTORY_MAX_ITEMS"
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
