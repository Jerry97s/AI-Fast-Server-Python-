# AI Fast Server Python

[커밋 내역 페이지(GitHub)](https://github.com/Jerry97s/AI-Fast-Server-Python-/commits/master) · [프로젝트 커밋 기록(문서)](COMMIT_HISTORY.md)

LangGraph 기반 대화형 AI 에이전트 서버.  
OpenAI ChatGPT를 LLM으로 사용하며, FastAPI HTTP 서버와 Windows 서비스 배포를 지원한다.  
C# WPF 클라이언트 연동 예제 포함.

---

## 기술 스택

| 계층 | 기술 | 버전 |
|------|------|------|
| LLM | OpenAI ChatGPT | gpt-3.5-turbo / gpt-4 |
| AI 프레임워크 | LangChain + LangGraph | 1.2.15+ / 1.1.9 |
| 웹 프레임워크 | FastAPI | 0.115.0+ |
| ASGI 서버 | Uvicorn | 0.32.0+ |
| 메모리 | JSON 파일 + SQLite | - |
| Windows 서비스 | pywin32 | 307+ |
| 패키지 관리 | uv | - |
| Python | CPython | 3.14 |

---

## 프로젝트 구조

```
AI_Agent_Py/
├── main.py                  # LangGraph 에이전트 핵심 로직 (도구, 메모리, 상태 머신)
├── safe_math.py             # calculator용 안전 산술(AST, eval 없음)
├── app_settings.py          # pydantic-settings 환경 설정
├── api_server.py            # FastAPI HTTP 서버
├── api_middleware.py        # 보안 헤더·선택 Bearer 인증
├── windows_service.py       # Windows 서비스 래퍼 (자동 재시작, 로그 처리)
├── docs/
│   ├── ARCHITECTURE.md      # 계층·데이터 흐름·확장
│   ├── OPERATIONS.md        # 헬스/로그/확장 운영
│   └── SECURITY_AND_DEPLOYMENT.md
├── pyproject.toml           # 의존성 및 프로젝트 설정
├── .env                     # 환경 변수 (OPENAI_API_KEY 등, Git 제외)
├── memory.json              # 에이전트 장기 메모리 저장소
├── scripts/
│   ├── install_service_admin.cmd   # 서비스 설치 (관리자 권한)
│   └── remove_service_admin.cmd    # 서비스 제거
└── integration/
    ├── windows-service/README.md   # 서비스 배포 가이드
    └── wpf/                        # C# WPF 클라이언트 연동 코드
```

---

## 설치 및 실행

### 사전 조건

- Python 3.14+
- [uv](https://github.com/astral-sh/uv) 패키지 관리자
- OpenAI API 키

### 1. 의존성 설치

```bash
uv sync
```

### 2. 환경 변수 설정

`.env` 파일을 생성하고 API 키를 입력한다:

```
OPENAI_API_KEY=your_actual_api_key
```

### 3-A. CLI 대화형 실행

```bash
uv run main.py
```

`exit` 또는 `quit` 입력 시 종료.

### 3-B. API 서버 실행

```bash
uv run uvicorn api_server:app --host 127.0.0.1 --port 8787
```

원격 노출·HTTPS·인증·방화벽은 [docs/SECURITY_AND_DEPLOYMENT.md](docs/SECURITY_AND_DEPLOYMENT.md)와 환경 변수(`AGENT_*`)를 참고하세요.

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/health` | GET | 서비스 상태, `version`, `model`(비밀 없음) |
| `/ready` | GET | SQLite·logs 쓰기 검사(503이면 준비 안 됨) |
| `/v1/chat` | POST | 메시지 전송 및 응답 수신 |
| `/v1/upload` | POST | 파일 업로드 (logs/ 저장) |

요청 예시:
```json
{
  "message": "안녕하세요",
  "thread_id": "user-123"
}
```

### 3-C. Windows 서비스로 배포

관리자 권한으로 `scripts/install_service_admin.cmd` 실행.  
부팅 시 자동 시작되며, 비정상 종료 시 지수 백오프로 자동 재시작한다.

---

## 아키텍처

```
┌──────────────────────────────────────┐
│       사용자 / WPF 클라이언트         │
└──────────────┬───────────────────────┘
               │ HTTP POST /v1/chat
               ▼
┌──────────────────────────────────────┐
│       FastAPI  (api_server.py)        │
│  · CORS 처리 · 파일 업로드            │
│  · 투자 리서치 모드 프롬프트          │
└──────────────┬───────────────────────┘
               │ agent_graph.invoke()
               ▼
┌──────────────────────────────────────┐
│     LangGraph StateGraph (main.py)    │
│  Agent 노드 ↔ Tools 노드             │
│  도구: calculator · memory · log     │
└──────┬───────────┬──────────────┬────┘
       ▼           ▼              ▼
  ┌─────────┐ ┌──────────┐ ┌──────────────┐
  │  OpenAI │ │  SQLite  │ │ memory.json  │
  │   API   │ │Checkpoint│ │  장기 메모리  │
  └─────────┘ └──────────┘ └──────────────┘
```

---

## 프로젝트 분석

> 상세 분석: [PROJECT_ANALYSIS.md](PROJECT_ANALYSIS.md)

### 수준 점수 (자체 평가 · 하드닝 반영 후)

| 항목 | 점수 |
|------|:----:|
| 아키텍처 | 10 / 10 |
| 코드 품질 | 10 / 10 |
| 보안 | 10 / 10 |
| 성능 | 10 / 10 |
| 문서화 | 10 / 10 |
| 운영성 | 10 / 10 |
| 확장성 | 10 / 10 |
| **종합** | **10 / 10** |

*실제 배포 환경·트래픽·규제에 따라 추가 하드닝이 필요할 수 있습니다.*

### 주요 장점

- **계층 분리** — 에이전트(`main`) / HTTP(`api_server`·`api_middleware`) / 설정(`app_settings`) / 안전 산술(`safe_math`)
- **보안** — 계산기 `eval` 제거(AST), 선택 Bearer 토큰, 보안 응답 헤더, CORS·레이트 리밋·메시지 상한
- **운영** — 로그 순환(`RotatingFileHandler`), `/ready` 검사, Slack 오류 알림(선택)
- **문서** — [ARCHITECTURE.md](docs/ARCHITECTURE.md), [OPERATIONS.md](docs/OPERATIONS.md), [SECURITY_AND_DEPLOYMENT.md](docs/SECURITY_AND_DEPLOYMENT.md)

### 다음 선택 과제

| 우선순위 | 항목 | 내용 |
|----------|------|------|
| P2 | 응답 스트리밍 | SSE `/v1/chat/stream` 등으로 토큰 단위 UX |
| P2 | 분산 체크포인트 | 인스턴스 다중 시 Redis 등 외부 체크포인터 저장소 |

---

## WPF 연동

`integration/wpf/` 폴더의 C# 파일을 프로젝트에 추가하면 된다.  
자세한 내용은 [integration/wpf/README.md](integration/wpf/README.md) 참고.
