# AI Fast Server Python

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
├── api_server.py            # FastAPI HTTP 서버 (/v1/chat, /v1/upload, /health)
├── windows_service.py       # Windows 서비스 래퍼 (자동 재시작, 로그 처리)
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

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/health` | GET | 서비스 상태 확인 |
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

### 수준 점수

| 항목 | 점수 |
|------|:----:|
| 아키텍처 | 8.0 / 10 |
| 코드 품질 | 7.5 / 10 |
| 보안 | 6.5 / 10 |
| 성능 | 7.0 / 10 |
| 문서화 | 7.0 / 10 |
| 운영성 | 7.5 / 10 |
| 확장성 | 8.5 / 10 |
| **종합** | **7.4 / 10** |

### 주요 장점

- **계층 분리** — 에이전트 로직 / HTTP / 서비스 운영이 완전히 분리됨
- **한글 완벽 지원** — UTF-8/UTF-16 LE 처리, 한글 깨짐 방지 로직 내장
- **자동 재시작** — 지수 백오프(2s→30s)로 서비스 다운 최소화
- **보안 의식** — 경로 탈출 공격 방지, 메시지 크기 제한
- **높은 확장성** — 도구 추가·LLM 교체가 수 줄로 가능

### 주요 개선 과제

| 우선순위 | 항목 | 내용 |
|----------|------|------|
| P0 (즉시) | `eval()` 제거 | 계산기 도구의 임의 코드 실행 위험 → `ast.literal_eval()` 대체 |
| P0 (즉시) | CORS 명시화 | 기본값 `"*"` → `.env`에서 허용 도메인 명시 |
| P1 (단기) | 로그 순환 | `RotatingFileHandler` 적용 (무한 증가 방지) |
| P1 (단기) | 메모리 정리 | `memory.json` TTL 기반 만료 로직 추가 |
| P2 (중기) | 응답 스트리밍 | FastAPI SSE로 실시간 토큰 출력 |

---

## WPF 연동

`integration/wpf/` 폴더의 C# 파일을 프로젝트에 추가하면 된다.  
자세한 내용은 [integration/wpf/README.md](integration/wpf/README.md) 참고.
