"""

AI Agent HTTP API — C# WPF 등 외부 클라이언트에서 LangGraph 에이전트를 호출할 때 사용.



실행 (프로젝트 루트에서):

  uv run uvicorn api_server:app --host 127.0.0.1 --port 8787



설정은 `app_settings`(환경 변수·`.env`)를 참조합니다.

원격 노출 시 HTTPS·인증·방화벽은 docs/SECURITY_AND_DEPLOYMENT.md 를 따르세요.

"""

from __future__ import annotations

import logging
import os
import sqlite3
import time
import traceback
import uuid
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware

from api_middleware import BearerAuthMiddleware, SecurityHeadersMiddleware
from app_settings import get_settings, mask_preview
from slack_notifier import send_slack_error

_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

load_dotenv(dotenv_path=os.path.join(_PROJECT_ROOT, ".env"))


# main.py에서 컴파일된 그래프 사용 (모델은 app_settings 기반으로 연결됨)

from main import app as agent_graph, bind_chat_thread_id  # noqa: E402, I001

_settings = get_settings()

DEFAULT_HOST = _settings.agent_api_host

DEFAULT_PORT = _settings.agent_api_port

_BEARER_TOKEN = (
    _settings.agent_api_bearer_token.get_secret_value()
    if _settings.agent_api_bearer_token
    else None
)


_CHECKPOINT_DB_PATH = os.path.join(_PROJECT_ROOT, "agent_checkpoint.db")


def _cors_origins_list() -> list[str]:

    raw = (_settings.agent_cors_origins or "").strip()

    if raw == "*":
        return ["*"]

    return [x.strip() for x in raw.split(",") if x.strip()]


def _error_payload(
    code: str,
    message: str,
    *,
    details: Any | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:

    err: dict[str, Any] = {"code": code, "message": message}

    if details is not None:
        err["details"] = details

    body: dict[str, Any] = {"error": err}

    if request_id:
        body["request_id"] = request_id

    return body


def _json_error(
    status_code: int,
    code: str,
    message: str,
    *,
    details: Any | None = None,
    request_id: str | None = None,
) -> JSONResponse:

    return JSONResponse(
        status_code=status_code,
        content=_error_payload(code, message, details=details, request_id=request_id),
    )


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=20000, description="사용자 메시지")

    thread_id: str = Field(
        default="wpf-default",
        description="대화 스레드 ID (WPF에서는 창/사용자별로 구분 권장)",
    )

    mode: str | None = Field(
        default=None,
        description="응답 모드 (예: invest). 미지정 시 기본 대화.",
    )


class ChatResponse(BaseModel):
    reply: str

    thread_id: str


_INVEST_SYSTEM_PROMPT = (
    "너는 한국어로 답변하는 투자 리서치 어시스턴트다.\n"
    "중요: 특정 종목/코인에 대해 '매수/매도/추천/목표가/비중/언제 사라' 같은 직접적인 투자지시를 하지 않는다.\n"
    "대신 아래 형태로만 답한다.\n\n"
    "1) 요약(3줄): 현재 쟁점/핵심 리스크/확인해야 할 것\n"
    "2) 체크리스트: (재무/밸류/모멘텀/수급/리스크/매크로/규제) 관점에서 확인 항목\n"
    "3) 시나리오 분석: 낙관/기준/비관 시나리오별 촉발 요인과 관찰 지표\n"
    "4) 리스크 관리(일반론): 손실 제한 원칙, 변동성/유동성/분산 관점\n"
    "5) 사용자에게 물어볼 질문 5개: 투자기간, 위험선호, 손실한도, 보유자산, 현금흐름 등\n\n"
    "사용자가 '추천해줘'라고 해도 위 형식을 유지한다. 결정은 사용자 본인이 하도록 하고, "
    "나는 정보 정리·리스크 분석만 제공한다."
)


def _last_assistant_text(result: dict) -> str:

    from langchain_core.messages import AIMessage

    msgs = result.get("messages") or []

    for m in reversed(msgs):
        if isinstance(m, AIMessage) or getattr(m, "type", None) == "ai":
            c = getattr(m, "content", None)

            if c is None:
                continue

            if isinstance(c, str) and c.strip():
                return c

            if isinstance(c, list):
                parts = []

                for block in c:
                    if isinstance(block, dict) and block.get("type") == "text":
                        parts.append(block.get("text", ""))

                    elif isinstance(block, str):
                        parts.append(block)

                return "\n".join(p for p in parts if p) or str(c)

            return str(c)

    return ""


def _classify_agent_error(exc: BaseException) -> tuple[str, int, str]:
    """클라이언트용 코드·HTTP 상태·한국어 메시지."""

    try:
        import httpx

    except ImportError:
        httpx = None  # type: ignore

    APITimeoutError = RateLimitError = APIError = None

    try:
        from openai import APIError as _APIE
        from openai import APITimeoutError as _APT
        from openai import RateLimitError as _RL

        APITimeoutError, RateLimitError, APIError = _APT, _RL, _APIE

    except ImportError:
        pass

    if isinstance(exc, TimeoutError):
        return (
            "model_timeout",
            504,
            "모델 응답 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요.",
        )

    if httpx is not None:
        if isinstance(exc, httpx.TimeoutException):
            return (
                "model_timeout",
                504,
                "모델 응답 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요.",
            )

        if isinstance(exc, httpx.ConnectError):
            return (
                "model_unreachable",
                502,
                "모델 서버에 연결할 수 없습니다. 네트워크·BASE URL·방화벽을 확인해 주세요.",
            )

    if APITimeoutError is not None and isinstance(exc, APITimeoutError):
        return (
            "model_timeout",
            504,
            "모델 응답 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요.",
        )

    if RateLimitError is not None and isinstance(exc, RateLimitError):
        return (
            "model_rate_limited",
            429,
            "모델 제공자 쪽 요청 한도에 걸렸습니다. 잠시 후 다시 시도해 주세요.",
        )

    if APIError is not None and isinstance(exc, APIError):
        return (
            "model_error",
            502,
            "모델 호출 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
        )

    return (
        "agent_error",
        502,
        "에이전트 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
    )


_LOG_DIR = os.path.join(_PROJECT_ROOT, "logs")

os.makedirs(_LOG_DIR, exist_ok=True)

_API_ERR_LOG_PATH = os.path.join(_LOG_DIR, "api-errors.log")


_logger = logging.getLogger("ai_agent_api")

if not _logger.handlers:
    _logger.setLevel(logging.INFO)

    _fh = RotatingFileHandler(
        _API_ERR_LOG_PATH,
        maxBytes=_settings.agent_log_max_bytes,
        backupCount=_settings.agent_log_backup_count,
        encoding="utf-8",
    )

    _fh.setLevel(logging.INFO)

    _fh.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(message)s"))

    _logger.addHandler(_fh)


@asynccontextmanager
async def _lifespan(app: FastAPI):

    if _settings.agent_cors_origins.strip() == "*" and _settings.agent_api_host not in (
        "127.0.0.1",
        "::1",
        "localhost",
    ):
        _logger.warning(
            "AGENT_CORS_ORIGINS=* 로 외부 바인드 호스트(%s)에 배포 중입니다. "
            "프로덕션에서는 출처를 제한하세요.",
            _settings.agent_api_host,
        )

    if _BEARER_TOKEN:
        _logger.info("AGENT_API_BEARER_TOKEN 설정됨 — Bearer 인증 활성.")

    yield


app = FastAPI(
    title="AI Agent API",
    version=_settings.app_version,
    lifespan=_lifespan,
)


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):

        rid = request.headers.get("x-request-id") or str(uuid.uuid4())

        request.state.request_id = rid

        response = await call_next(request)

        response.headers["X-Request-ID"] = rid

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """분당 동일 클라이언트 IP 요청 수 제한 (비활성: AGENT_RATE_LIMIT_PER_MINUTE=0)."""

    def __init__(self, app, requests_per_minute: int):

        super().__init__(app)

        self.requests_per_minute = requests_per_minute

        self._minute_index: int = -1

        self._counts: dict[str, int] = {}

    async def dispatch(self, request: Request, call_next):

        if self.requests_per_minute <= 0:
            return await call_next(request)

        path = request.url.path

        if path in ("/health", "/ready", "/", "/docs", "/openapi.json", "/redoc"):
            return await call_next(request)

        now_min = int(time.time() // 60)

        if now_min != self._minute_index:
            self._minute_index = now_min

            self._counts.clear()

        client = request.client

        host = client.host if client else "unknown"

        key = host

        self._counts[key] = self._counts.get(key, 0) + 1

        if self._counts[key] > self.requests_per_minute:
            rid = getattr(request.state, "request_id", None)

            return _json_error(
                429,
                "rate_limit_exceeded",
                "요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.",
                request_id=rid,
            )

        return await call_next(request)


app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=_settings.agent_rate_limit_per_minute,
)

app.add_middleware(BearerAuthMiddleware, bearer_token=_BEARER_TOKEN)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(RequestIdMiddleware)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):

    rid = getattr(request.state, "request_id", None)

    return _json_error(
        422,
        "validation_error",
        "요청 형식이 올바르지 않습니다.",
        details=exc.errors(),
        request_id=rid,
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):

    rid = getattr(request.state, "request_id", None)

    detail = exc.detail

    code_map = {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        413: "payload_too_large",
        429: "rate_limit_exceeded",
        500: "internal_error",
        502: "bad_gateway",
        504: "gateway_timeout",
    }

    if isinstance(detail, dict) and "message" in detail:
        code = str(detail.get("code") or code_map.get(exc.status_code, f"http_{exc.status_code}"))

        msg = str(detail["message"])

        return _json_error(exc.status_code, code, msg, request_id=rid)

    if isinstance(detail, list):
        msg = str(detail)

        code = "validation_error"

    else:
        msg = str(detail)

        code = code_map.get(exc.status_code, f"http_{exc.status_code}")

    return _json_error(exc.status_code, code, msg, request_id=rid)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):

    tb = traceback.format_exc()

    rid = getattr(request.state, "request_id", None)

    _logger.error(
        "Unhandled exception request_id=%s path=%s %s\n%s",
        rid,
        request.url.path,
        type(exc).__name__,
        tb,
    )

    send_slack_error(
        title=f"AI Agent API Unhandled Exception ({request.method} {request.url.path})",
        text=tb[-3500:],
        signature=f"unhandled:{type(exc).__name__}:{request.url.path}",
    )

    return _json_error(
        500,
        "internal_error",
        "서버 내부 오류가 발생했습니다. 관리자에게 문의하거나 잠시 후 다시 시도해 주세요.",
        request_id=rid,
    )


@app.get("/ready")
def ready():
    """체크포인트 SQLite·logs 쓰기 가능 여부(로드밸런서용)."""

    checks: dict[str, str] = {}

    ok = True

    try:
        conn = sqlite3.connect(_CHECKPOINT_DB_PATH, timeout=3.0)

        try:
            conn.execute("SELECT 1")

        finally:
            conn.close()

        checks["checkpoint_sqlite"] = "ok"

    except Exception as e:
        checks["checkpoint_sqlite"] = f"fail:{type(e).__name__}"

        ok = False

    probe = os.path.join(_LOG_DIR, ".write_probe")

    try:
        with open(probe, "w", encoding="utf-8") as f:
            f.write("ok")

        os.remove(probe)

        checks["logs_writable"] = "ok"

    except Exception as e:
        checks["logs_writable"] = f"fail:{type(e).__name__}"

        ok = False

    payload = {"ready": ok, "checks": checks, "version": _settings.app_version}

    return JSONResponse(status_code=200 if ok else 503, content=payload)


@app.get("/health")
def health():

    return {
        "status": "ok",
        "version": _settings.app_version,
        "agent": "langgraph",
        "model": _settings.agent_model,
    }


@app.post("/v1/upload")
async def upload(request: Request, file: UploadFile = File(...)):
    """클라이언트에서 파일을 업로드하면 서버의 logs 폴더에 저장하고 파일명을 반환."""

    rid = getattr(request.state, "request_id", None)

    try:
        filename = os.path.basename(file.filename or "uploaded.txt")

        save_path = os.path.join(_LOG_DIR, filename)

        content = await file.read()

        max_upload = int(os.getenv("AGENT_UPLOAD_MAX_BYTES", str(25 * 1024 * 1024)))

        if len(content) > max_upload:
            raise HTTPException(
                status_code=413,
                detail=f"파일 크기가 너무 큽니다. 최대 {max_upload}바이트까지 허용됩니다.",
            )

        with open(save_path, "wb") as f:
            f.write(content)

        _logger.info(
            "uploaded filename=%s bytes=%s request_id=%s",
            filename,
            len(content),
            rid,
        )

        return {"filename": filename, "bytes": len(content)}

    except HTTPException:
        raise

    except Exception as e:
        tb = traceback.format_exc()

        _logger.error("upload failed request_id=%s\n%s", rid, tb)

        send_slack_error(
            title="AI Agent API upload failed",
            text=tb[-3500:],
            signature=f"upload:{type(e).__name__}",
        )

        raise HTTPException(
            status_code=500,
            detail={
                "code": "upload_failed",
                "message": "파일 업로드 처리 중 오류가 발생했습니다.",
            },
        ) from e


def _run_chat(body: ChatRequest, request: Request) -> ChatResponse:

    rid = getattr(request.state, "request_id", None)

    preview = mask_preview(body.message)

    _logger.info(
        "chat thread_id=%s mode=%s message_preview=%s request_id=%s",
        body.thread_id,
        body.mode,
        preview,
        rid,
    )

    config = {"configurable": {"thread_id": body.thread_id}}

    messages = []

    if (body.mode or "").lower() == "invest":
        messages.append(SystemMessage(content=_INVEST_SYSTEM_PROMPT))

    messages.append(HumanMessage(content=body.message))

    try:
        with bind_chat_thread_id(body.thread_id):
            result = agent_graph.invoke({"messages": messages}, config=config)

    except HTTPException:
        raise

    except Exception as e:
        tb = traceback.format_exc()

        code, status, msg = _classify_agent_error(e)

        _logger.error(
            "chat invoke failed thread_id=%s mode=%s code=%s request_id=%s\n%s",
            body.thread_id,
            body.mode,
            code,
            rid,
            tb,
        )

        send_slack_error(
            title=f"AI Agent API chat failed ({code}, thread_id={body.thread_id})",
            text=tb[-3500:],
            signature=f"chat:{type(e).__name__}:{code}",
        )

        raise HTTPException(
            status_code=status,
            detail={"code": code, "message": msg},
        ) from e

    reply = _last_assistant_text(result)

    if not reply:
        reply = "(응답이 비어 있습니다. 도구 호출만 있었을 수 있습니다.)"

    return ChatResponse(reply=reply, thread_id=body.thread_id)


@app.post("/v1/chat", response_model=ChatResponse)
def chat_v1(body: ChatRequest, request: Request):

    try:
        return _run_chat(body, request)

    except HTTPException:
        raise

    except Exception as e:
        tb = traceback.format_exc()

        rid = getattr(request.state, "request_id", None)

        _logger.error(
            "chat failed thread_id=%s request_id=%s\n%s",
            body.thread_id,
            rid,
            tb,
        )

        send_slack_error(
            title=f"AI Agent API chat failed (thread_id={body.thread_id}, mode={body.mode})",
            text=tb[-3500:],
            signature=f"chat:{type(e).__name__}",
        )

        raise HTTPException(
            status_code=500,
            detail={
                "code": "internal_error",
                "message": "대화 처리 중 알 수 없는 오류가 발생했습니다.",
            },
        ) from e


@app.post("/chat", response_model=ChatResponse)
def chat_legacy(body: ChatRequest, request: Request):

    return chat_v1(body, request)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api_server:app",
        host=DEFAULT_HOST,
        port=DEFAULT_PORT,
        reload=False,
    )
