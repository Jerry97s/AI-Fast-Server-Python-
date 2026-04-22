# C# WPF ↔ Python AI Agent 연동

## 1. Python 쪽: API 서버 실행

AI_Agent_Py 프로젝트 루트에서 (`.env`에 `OPENAI_API_KEY` 등 설정):

```text
pip install -e . -q
python -m uvicorn api_server:app --host 127.0.0.1 --port 8787
```

또는 (uv 사용 시) `uv run python -m uvicorn api_server:app --host 127.0.0.1 --port 8787`

- 헬스 확인: 브라우저에서 `http://127.0.0.1:8787/health`
- 기본 포트는 `8787`. 바꿀 경우 WPF의 `AiAgentClient` 생성자 URL도 같이 수정.

환경 변수 (선택):

| 변수 | 의미 |
|------|------|
| `AGENT_API_HOST`, `AGENT_API_PORT` | `python api_server.py` 로 직접 띄울 때 호스트·포트 |
| `AGENT_CORS_ORIGINS` | 기본 `*` (개발용). 필요 시 `http://localhost:포트` 등으로 제한 |

## 2. WPF 프로젝트 설정

1. 타깃 프레임워크: 권장 **.NET 6 이상** (시스템 HttpClient · System.Text.Json 기본 포함).
2. 이 폴더의 `AiAgentClient.cs`를 프로젝트에 추가합니다.
3. 네임스페이스 `YourApp.Integration`을 실제 프로젝트 네임스페이스로 바꿉니다.
4. `MainWindowChatExample.xaml.cs`는 참고용입니다. UI 컨트롤 이름(`UserInputTextBox`, `ReplyTextBlock`, `SendButton`)을 본인 XAML에 맞게 수정하세요.

## 3. API 계약

`POST /v1/chat`

요청 JSON:

```json
{ "message": "안녕", "thread_id": "선택-대화별-ID" }
```

응답 JSON:

```json
{ "reply": "에이전트 답변", "thread_id": "..." }
```

`thread_id`로 대화 상태를 구분합니다 (LangGraph checkpoint). 한 WPF 창당 하나의 GUID를 쓰면 해당 창에서만 문맥이 유지됩니다.

## 4. 배포 시 참고

- 개발: WPF와 같은 PC에서 Agent API를 로컬로 띄움.
- 운영: Agent API를 별도 서버/서비스로 두고 WPF에서 `AiAgentClient("http://서버주소:8787/")`로 지정. 방화벽·HTTPS는 환경에 맞게 구성.
