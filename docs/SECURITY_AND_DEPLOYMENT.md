# 보안 및 배포

## 네트워크 노출

- **기본값**: API는 `AGENT_API_HOST=127.0.0.1`(로컬 루프백)에서만 수신하는 것을 권장합니다. WPF 등 동일 PC 클라이언트는 이 구성으로 충분합니다.
- **원격 노출 시** 다음을 함께 적용해야 합니다.
  - **HTTPS**: TLS 종료(역방향 프록시 또는 uvicorn TLS).
  - **인증**: API 키·클라이언트 인증서·VPN 등으로 무단 호출을 차단합니다.
  - **방화벽**: 필요한 소스 IP·포트만 허용합니다.

## 비밀 관리

- `OPENAI_API_KEY`, Slack 토큰 등은 **코드에 넣지 말고** 환경 변수 또는 OS·배포 플랫폼의 시크릿 저장소만 사용합니다.
- 시크릿이 채팅·로그에 노출된 경우 **즉시 폐기하고 재발급**합니다.

## 로깅

- 클라이언트 메시지 전문은 로그에 남기지 않습니다. API는 요약 미리보기(`AGENT_LOG_MESSAGE_PREVIEW_CHARS`)만 기록합니다.

## 설정 참조

주요 환경 변수는 `app_settings.py` 및 `.env` 예시를 참고하세요.

- `AGENT_MODEL`, `AGENT_LLM_TIMEOUT_SECONDS`, `AGENT_LLM_MAX_TOKENS`
- `OPENAI_API_BASE` (Azure 게이트웨어·OpenAI 호환 로컬 서버 등)
- `AGENT_RATE_LIMIT_PER_MINUTE` (`0`이면 분당 제한 비활성)
- **`AGENT_CORS_ORIGINS`**: 쉼표 구분 출처 목록. 프로덕션에서는 `*` 대신 명시 권장.
- **`AGENT_API_BEARER_TOKEN`**: 설정 시 `/v1/chat`, `/v1/upload` 등에 `Authorization: Bearer …` 필요 (`/health`, `/ready`, 문서 경로 제외).

## 헬스·준비 상태

- `GET /health`: 버전과 **모델 이름**(비밀 없음).
- `GET /ready`: SQLite 체크포인트·로그 디렉터리 쓰기 가능 여부 (503 시 트래픽 차단 권장).

## 응답 보안 헤더

API는 `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy` 등 기본 헤더를 붙입니다.
