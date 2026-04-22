"""
AI Agent HTTP API — C# WPF 등 외부 클라이언트에서 LangGraph 에이전트를 호출할 때 사용.

실행 (프로젝트 루트에서):
  uv run uvicorn api_server:app --host 127.0.0.1 --port 8787

환경 변수: AGENT_API_HOST, AGENT_API_PORT (기본 127.0.0.1:8787)
"""

from __future__ import annotations

import os
import traceback
import logging

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage

_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
load_dotenv(dotenv_path=os.path.join(_PROJECT_ROOT, ".env"))

# main.py에서 컴파일된 그래프 · 메시지 타입 사용
from main import app as agent_graph

DEFAULT_HOST = os.getenv("AGENT_API_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.getenv("AGENT_API_PORT", "8787"))


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="사용자 메시지")
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


app = FastAPI(title="AI Agent API", version="0.1.0")

_LOG_DIR = os.path.join(_PROJECT_ROOT, "logs")
os.makedirs(_LOG_DIR, exist_ok=True)
_API_ERR_LOG_PATH = os.path.join(_LOG_DIR, "api-errors.log")

_logger = logging.getLogger("ai_agent_api")
if not _logger.handlers:
    _logger.setLevel(logging.INFO)
    _fh = logging.FileHandler(_API_ERR_LOG_PATH, encoding="utf-8")
    _fh.setLevel(logging.INFO)
    _fh.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(message)s"))
    _logger.addHandler(_fh)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("AGENT_CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    _logger.error(
        "Unhandled exception on %s %s\n%s",
        request.method,
        request.url.path,
        traceback.format_exc(),
    )
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.get("/health")
def health():
    return {"status": "ok", "agent": "langgraph"}

@app.post("/v1/upload")
async def upload(file: UploadFile = File(...)):
    """클라이언트에서 파일을 업로드하면 서버의 logs 폴더에 저장하고 파일명을 반환."""
    try:
        filename = os.path.basename(file.filename or "uploaded.txt")
        save_path = os.path.join(_LOG_DIR, filename)
        content = await file.read()
        with open(save_path, "wb") as f:
            f.write(content)
        _logger.info("uploaded filename=%s bytes=%s", filename, len(content))
        return {"filename": filename, "bytes": len(content)}
    except Exception as e:
        _logger.error("upload failed\n%s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/v1/chat", response_model=ChatResponse)
def chat(body: ChatRequest):
    try:
        _logger.info(
            "chat request thread_id=%s mode=%s message_len=%s",
            body.thread_id,
            body.mode,
            len(body.message or ""),
        )
        if body.message and len(body.message) > 20000:
            raise HTTPException(
                status_code=413,
                detail="메시지가 너무 깁니다. 파일은 /v1/upload 로 업로드하고, 파일명으로 분석을 요청하세요.",
            )
        config = {"configurable": {"thread_id": body.thread_id}}
        messages = []
        if (body.mode or "").lower() == "invest":
            messages.append(SystemMessage(content=_INVEST_SYSTEM_PROMPT))
        messages.append(HumanMessage(content=body.message))
        result = agent_graph.invoke(
            {"messages": messages},
            config=config,
        )
        reply = _last_assistant_text(result)
        if not reply:
            reply = "(응답이 비어 있습니다. 도구 호출만 있었을 수 있습니다.)"
        return ChatResponse(reply=reply, thread_id=body.thread_id)
    except Exception as e:
        _logger.error(
            "chat failed thread_id=%s mode=%s\n%s",
            body.thread_id,
            body.mode,
            traceback.format_exc(),
        )
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/chat", response_model=ChatResponse)
def chat_legacy(body: ChatRequest):
    # 일부 클라이언트가 /chat 로 호출하는 경우 호환용 엔드포인트
    return chat(body)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api_server:app",
        host=DEFAULT_HOST,
        port=DEFAULT_PORT,
        reload=False,
    )
