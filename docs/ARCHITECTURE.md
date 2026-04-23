# 아키텍처

## 계층

| 계층 | 모듈 | 책임 |
|------|------|------|
| HTTP·운영 | `api_server.py`, `api_middleware.py` | 라우팅, 검증, 레이트 리밋, 보안 헤더, 선택 Bearer, 로그 순환 |
| 설정 | `app_settings.py` | `pydantic-settings` 기반 환경 변수 (비밀 분리) |
| 에이전트 | `main.py` | LangGraph 그래프, 도구, 한글 시스템 프롬프트, SQLite 체크포인트 |
| 안전 산술 | `safe_math.py` | 도구 `calculator` 전용 AST 기반 평가 (`eval` 없음) |
| 알림 | `slack_notifier.py` | 오류 시 Slack (선택) |
| 서비스 호스트 | `windows_service.py` | Windows 서비스로 uvicorn 자식 프로세스 관리 |

## 데이터 흐름

1. 클라이언트 → `POST /v1/chat` → (선택) Bearer 검증 → 레이트 리밋 → `_run_chat`
2. LangGraph `invoke` → `call_model` / `call_tools` 반복 → 마지막 AI 메시지 텍스트 추출
3. 장기 메모리: `memory.json` (프로젝트 루트 고정), `history` 상한은 `AGENT_MEMORY_HISTORY_MAX_ITEMS`
4. 대화 문맥: `agent_checkpoint.db` + `SqliteSaver`

## 확장 포인트

- **다른 LLM**: `OPENAI_API_BASE` + 호환 키로 OpenAI 호환 엔드포인트 연결
- **도구 추가**: `main.py`의 `@tool` 함수 등록 후 `tools` 리스트에 추가
- **수평 확장**: 동일 인스턴스는 SQLite 체크포인트 파일 충돌 가능 → 스티키 세션 또는 외부 체크포인트 저장소로 이전 필요 ([OPERATIONS.md](OPERATIONS.md))
