# Windows에서 API를 **서비스**로 실행

Python API(`api_server.py`)를 부팅 후에도 백그라운드에서 유지하려면 Windows 서비스로 등록합니다.

## 방법 A: 이 저장소의 `windows_service.py` (pywin32)

### 1) 관리자 권한으로 터미널 열기

### 2) 프로젝트 루트에서

**중요:** `install` 할 때 사용한 **`python.exe` 경로가 그대로 서비스에 저장**됩니다. 가상환경을 쓰면 그 venv를 활성화한 뒤 같은 방식으로 설치하세요.

```bat
cd /d D:\경로\AI_Agent_Py
pip install pywin32
python windows_service.py install
python windows_service.py start
```

### 3) 확인

- 서비스 관리자(`services.msc`)에서 **AI Agent API (FastAPI)** 검색  
- 브라우저: `http://127.0.0.1:8787/health`

### 중지·제거

```bat
python windows_service.py stop
python windows_service.py remove
```

### 설정

| 항목 | 설명 |
|------|------|
| 포트·호스트 | 환경 변수 `AGENT_API_HOST`, `AGENT_API_PORT` 또는 프로젝트 루트 `.env` |
| API 키 등 | 프로젝트 루트 `.env` — 자식 프로세스(uvicorn)가 `cwd` 기준으로 로드 |
| 계정 | 기본은 **Local System**. 다른 계정으로 실행하려면 서비스 속성에서 로그온 계정 변경 |

서비스는 프로젝트 폴더에서 `python -m uvicorn api_server:app ...` 자식 프로세스를 띄웁니다.

---

## 방법 B: NSSM (코드 없이 exe 감싸기)

[NSSM](https://nssm.cc/)으로 같은 uvicorn 명령을 서비스로 등록할 수 있습니다. Python 경로·작업 디렉터리(프로젝트 루트)·인수만 맞추면 됩니다.

---

## WPF 클라이언트

서비스가 같은 PC에서 `127.0.0.1:8787` 을 열어두면, 기존 WPF는 **`AiAgentClient`의 URL만** 맞추면 됩니다.
