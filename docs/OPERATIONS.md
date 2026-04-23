# 운영

## 헬스·준비 상태

| 경로 | 용도 |
|------|------|
| `GET /health` | 프로세스 살아 있음, 버전·모델명(비밀 없음) |
| `GET /ready` | 체크포인트 SQLite `SELECT 1`, `logs/` 쓰기 테스트 — 로드밸런서 준비 판별에 사용 |

## 로그

- 애플리케이션 오류 로그: `logs/api-errors.log`
- **순환**: `RotatingFileHandler` — `AGENT_LOG_MAX_BYTES`, `AGENT_LOG_BACKUP_COUNT`
- 사용자 메시지 전문은 기록하지 않으며 미리보기만 남김 (`AGENT_LOG_MESSAGE_PREVIEW_CHARS`)

## 보안 운영

- 원격 노출 시 `AGENT_API_BEARER_TOKEN` 설정 후 클라이언트에 `Authorization: Bearer <token>` 요구
- CORS: 프로덕션에서는 `AGENT_CORS_ORIGINS`에 허용 출처만 나열 (`*` 지양)

## 성능·확장

- 단일 프로세스 기본: CPU 바운드 LLM 호출은 워커 수를 과도하게 늘리지 않음
- 다중 인스턴스: 세션 고정(스티키) 또는 체크포인트를 공유 저장소로 이전하지 않으면 대화 스레드가 일관되지 않을 수 있음

## CI

GitHub Actions에서 `pip install -e ".[dev]"` 후 `pytest` 실행 ([`.github/workflows/ci.yml`](../.github/workflows/ci.yml)).
