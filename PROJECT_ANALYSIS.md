# AI Fast Server Python — 프로젝트 분석 보고서

> 작성일: 2026-04-22  
> 분석 대상: AI_Agent_Py (LangGraph 기반 AI 에이전트 + FastAPI 서버)

---

## 1. 프로젝트 개요

OpenAI ChatGPT를 백엔드로 사용하는 대화형 AI 에이전트 서버 프로젝트.  
로컬 Windows 환경에서 백그라운드 서비스로 실행되며, C# WPF 클라이언트가 HTTP API를 통해 에이전트와 통신한다.

### 기술 스택

| 계층 | 기술 | 버전 |
|------|------|------|
| LLM | OpenAI ChatGPT | gpt-3.5-turbo / gpt-4 |
| AI 프레임워크 | LangChain + LangGraph | 1.2.15+ / 1.1.9 |
| 웹 프레임워크 | FastAPI | 0.115.0+ |
| ASGI 서버 | Uvicorn | 0.32.0+ |
| 메모리 저장소 | JSON 파일 + SQLite | - |
| Windows 서비스 | pywin32 (ServiceFramework) | 307+ |
| 클라이언트 | C# WPF (.NET 6+) | - |
| 패키지 관리 | uv | - |
| Python 버전 | CPython | 3.14 |

---

## 2. 프로젝트 구조

```
AI_Agent_Py/
├── main.py                          # LangGraph 에이전트 핵심 로직
├── api_server.py                    # FastAPI HTTP 서버
├── windows_service.py               # Windows 서비스 래퍼
├── pyproject.toml                   # 의존성 및 프로젝트 설정
├── .python-version                  # Python 버전 고정 (3.14)
├── .env                             # 환경 변수 (OPENAI_API_KEY 등)
├── memory.json                      # 에이전트 지속성 메모리
├── README.md                        # 프로젝트 설명
├── uv.lock                          # 의존성 잠금 파일
├── agent_checkpoint.db              # LangGraph 대화 상태 (SQLite)
├── memory.db                        # 메모리 보조 데이터베이스
├── scripts/
│   ├── install_service_admin.cmd    # Windows 서비스 설치 (관리자 권한)
│   └── remove_service_admin.cmd     # Windows 서비스 제거
├── integration/
│   ├── windows-service/
│   │   └── README.md               # 서비스 배포 가이드
│   └── wpf/                        # C# WPF 클라이언트 연동
│       ├── AiAgentClient.cs        # HTTP 클라이언트 구현
│       ├── AgentApiServiceStarter.cs # 서비스 자동 시작 헬퍼
│       ├── MainWindowChatExample.xaml.cs # UI 연동 예제
│       └── README.md               # WPF 연동 가이드
└── logs/                           # 런타임 로그 출력 폴더
```

### 파일별 역할 요약

| 파일 | 역할 | 코드량 |
|------|------|--------|
| `main.py` | LangGraph StateGraph 구성, 도구 정의, 메모리 관리 | 333줄 |
| `api_server.py` | FastAPI 엔드포인트, 파일 업로드, 투자 모드 | 192줄 |
| `windows_service.py` | pywin32 서비스 래퍼, 자동 재시작, 로그 처리 | 242줄 |

---

## 3. 아키텍처

```
┌──────────────────────────────────────┐
│       사용자 / WPF 클라이언트         │
└──────────────┬───────────────────────┘
               │ HTTP POST /v1/chat
               ▼
┌──────────────────────────────────────┐
│       FastAPI  (api_server.py)        │
│  - CORS 처리                          │
│  - 파일 업로드  (/v1/upload)          │
│  - 투자 리서치 모드 프롬프트          │
│  - 에러 로깅 (logs/api-errors.log)    │
└──────────────┬───────────────────────┘
               │ agent_graph.invoke()
               ▼
┌──────────────────────────────────────┐
│     LangGraph StateGraph (main.py)    │
│                                       │
│   ┌─────────────┐  ┌──────────────┐  │
│   │  Agent 노드 │◄►│  Tools 노드  │  │
│   └─────────────┘  └──────────────┘  │
│                                       │
│   도구 목록:                          │
│   · calculator        (수식 계산)     │
│   · memory_save/load/search (메모리)  │
│   · read_log_file     (로그 읽기)     │
│   · list_log_files    (파일 목록)     │
│   · set_log_directory (경로 변경)     │
└──────┬───────────┬──────────────┬────┘
       ▼           ▼              ▼
  ┌─────────┐ ┌──────────┐ ┌──────────────┐
  │  OpenAI │ │ SQLite   │ │ memory.json  │
  │   API   │ │Checkpoint│ │ (지속성 메모리)│
  └─────────┘ └──────────┘ └──────────────┘
```

### 데이터 흐름

1. 사용자 → WPF 또는 CLI로 메시지 입력
2. WPF → FastAPI `/v1/chat` POST 요청
3. FastAPI → `agent_graph.invoke()` 호출
4. LangGraph → Agent 노드(LLM 호출) → 도구 필요 시 Tools 노드 실행
5. 결과 → FastAPI → WPF 화면에 표시
6. 대화 상태 → SQLite 체크포인터 저장 (재시작 후 문맥 유지)
7. 사용자 정보 → `memory.json` 저장 (장기 기억)

---

## 4. 장점

### 4-1. 명확한 계층 분리
에이전트 로직(`main.py`), HTTP 계층(`api_server.py`), 운영 계층(`windows_service.py`)이 완전히 분리되어 있다. 각 파일이 단일 책임 원칙을 잘 따르며, LLM을 교체하거나 서비스 방식을 변경해도 다른 계층에 영향이 없다.

### 4-2. 한글 완벽 지원
Python 소스 전반의 한글 주석, UTF-8 강제 설정, 로그의 UTF-16 LE BOM 처리까지 Windows 한글 환경을 꼼꼼히 고려했다. 한글 깨짐을 방지하는 다중 인코딩 시도 로직이 `windows_service.py`에 구현되어 있다.

### 4-3. 견고한 자동 재시작 메커니즘
서비스가 비정상 종료되면 지수 백오프(2초 → 5초 → 10초 → 20초 → 30초)로 자동 재시작한다. 종료 신호 수신 시 30초 그레이스풀 셧다운도 지원해 운영 안정성이 높다.

### 4-4. 보안 의식 — 경로 탈출 공격 방지
`read_log_file()` 도구에서 `os.path.commonpath()`로 디렉터리 탈출(directory traversal) 공격을 방어한다. 메시지 크기 상한(사용자 4,000자, API 20,000자)과 컨텍스트 길이 제한(최대 20개 메시지, 14,000자)도 갖추고 있다.

### 4-5. 유연한 도구 확장성
LangGraph의 `tools` 리스트에 Python 함수를 추가하기만 하면 새 도구를 에이전트에 즉시 등록할 수 있다. LLM 모델 교체도 `ChatOpenAI` 인스턴스 한 줄만 변경하면 된다.

### 4-6. WPF 클라이언트 통합 완성도
`AiAgentClient.cs`는 IDisposable 패턴, 커스텀 예외(`AiAgentApiException`), 5분 타임아웃, Null 안전 처리를 모두 갖춘 실용적인 구현이다. `AgentApiServiceStarter.cs`는 WPF 시작 시 서비스 상태를 자동 확인하고 필요하면 기동한다.

---

## 5. 단점

### 5-1. `eval()` 사용 — 보안 취약점 (심각)
`main.py`의 계산기 도구가 사용자 입력을 `eval()`로 직접 실행한다.  
`__import__('os').system('...')` 같은 임의 코드 실행이 이론적으로 가능하다.  
현재는 LLM이 표현식을 생성하므로 완화되어 있지만, 사용자가 직접 수식을 입력할 수 있는 경우 실제 위협이 된다.

### 5-2. CORS 기본값 `"*"` — 프로덕션 위험 (중간)
`api_server.py`의 CORS 허용 출처가 환경 변수 미설정 시 모든 도메인(`*`)을 허용한다.  
로컬 전용 서비스라면 무방하지만, 외부 노출 시 크로스 사이트 요청 위조 공격 경로가 된다.

### 5-3. 로그 파일 순환 없음 — 무한 증가 (중간)
`logs/service-uvicorn.log`와 `logs/api-errors.log`는 크기 제한이나 순환(rotation) 로직이 없다.  
장기 운영 시 디스크를 소진할 수 있다.

### 5-4. 메모리 JSON 정리 로직 부재 (중간)
`memory.json`에 데이터가 누적되기만 하고 오래된 항목을 정리하는 로직이 없다.  
`conversation_history` 등 빠르게 커지는 키가 있을 경우 파일 크기가 계속 증가한다.

### 5-5. 파일 업로드 충돌 — 덮어쓰기 위험 (중간)
`/v1/upload` 엔드포인트는 같은 파일명으로 업로드하면 기존 파일을 그대로 덮어쓴다.  
타임스탬프나 UUID 접두사가 없어 의도치 않은 데이터 손실이 발생할 수 있다.

---

## 6. 개선점

### P0 — 즉시 수정 (보안 위험)

| # | 항목 | 현재 문제 | 권고 조치 |
|---|------|-----------|-----------|
| 1 | `eval()` 제거 | 임의 코드 실행 가능 | `ast.literal_eval()` 또는 `numexpr` 사용 |
| 2 | CORS 명시화 | 모든 도메인 허용 | `.env`에 `AGENT_CORS_ORIGINS=http://localhost` 설정 강제 |
| 3 | 파일 업로드 충돌 | 동일 파일명 덮어쓰기 | 저장 시 `{timestamp}_{filename}` 형식 적용 |

### P1 — 단기 개선 (운영 안정성)

| # | 항목 | 권고 조치 |
|---|------|-----------|
| 4 | 로그 파일 순환 | `logging.handlers.RotatingFileHandler` 적용 (최대 10MB, 5개 보관) |
| 5 | 메모리 정리 | 메모리 저장 시 키별 최대 항목 수 제한 + TTL 기반 만료 로직 추가 |
| 6 | 타입 힌팅 | 주요 함수에 Python 3.14 타입 어노테이션 추가 |
| 7 | 단위 테스트 | 도구 함수(`calculator`, `memory_save` 등) 단위 테스트 작성 |

### P2 — 중기 개선 (기능 확장)

| # | 항목 | 권고 조치 |
|---|------|-----------|
| 8 | 응답 스트리밍 | FastAPI SSE(Server-Sent Events)로 실시간 토큰 스트리밍 |
| 9 | 메모리 백엔드 교체 | JSON 파일 → Redis 또는 SQLite로 전환해 동시성·성능 개선 |
| 10 | 투자 모드 상태 관리 | 매 요청마다 시스템 프롬프트 추가하는 방식 → 스레드별 모드 상태 저장 |
| 11 | Docker 지원 | `Dockerfile` + `docker-compose.yml` 추가로 이식성 확보 |
| 12 | Linux/Mac 지원 | pywin32 의존성을 조건부 임포트로 변경해 크로스 플랫폼 호환 |

---

## 7. 수준 점수

| 항목 | 점수 | 평가 근거 |
|------|:----:|-----------|
| 아키텍처 | 8.0 / 10 | 계층 분리 명확, LangGraph 상태 머신 적절 활용, 단방향 의존성 유지 |
| 코드 품질 | 7.5 / 10 | 한글 지원 우수, 에러 메시지 명확, 일부 함수 길이 개선 필요 (call_model ~85줄) |
| 보안 | 6.5 / 10 | 경로 탈출 방어·크기 제한 양호, `eval()` 및 CORS 기본값이 점수 하락 요인 |
| 성능 | 7.0 / 10 | LLM API 호출 지연이 주 병목, 메모리 파일 I/O 캐싱 여지 있음 |
| 문서화 | 7.0 / 10 | README 간결, WPF 연동 가이드 충실, API 상세 명세 보강 필요 |
| 운영성 | 7.5 / 10 | 자동 재시작·지수 백오프 우수, 로그 순환 없음이 감점 요인 |
| 확장성 | 8.5 / 10 | 도구 추가·LLM 교체 매우 용이, 메모리 백엔드 교체 구조도 준비됨 |
| **종합** | **7.4 / 10** | |

### 종합 평가

> **완성도 높은 프로토타입 — 소규모 내부 운영 준비 단계**

LangGraph를 활용한 에이전트 설계와 Windows 서비스 통합은 실용적이고 견고하다.  
P0 항목(eval 제거, CORS 명시화, 파일 충돌 방지)만 해결하면 소규모 팀 내부 도구로 즉시 운영 가능한 수준이다.  
P1 항목까지 완료하면 장기 운영에도 안정적인 프로덕션 서비스로 전환할 수 있다.
