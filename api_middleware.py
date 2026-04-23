"""FastAPI / Starlette 미들웨어 (보안 헤더·선택 Bearer 인증)."""

from __future__ import annotations

import secrets

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """브라우저·프록시 기본 보안 헤더."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=()")
        return response


class BearerAuthMiddleware(BaseHTTPMiddleware):
    """
    AGENT_API_BEARER_TOKEN 이 설정된 경우에만 활성화.
    /health, /ready, OpenAPI 문서 등은 예외.
    """

    PUBLIC_PATHS = frozenset(
        {
            "/",
            "/health",
            "/ready",
            "/docs",
            "/redoc",
            "/openapi.json",
        }
    )

    def __init__(self, app, bearer_token: str | None):
        super().__init__(app)
        self._token = bearer_token

    async def dispatch(self, request: Request, call_next):
        if not self._token:
            return await call_next(request)
        path = request.url.path
        if path in self.PUBLIC_PATHS:
            return await call_next(request)
        auth = request.headers.get("authorization") or ""
        if not auth.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={
                    "error": {
                        "code": "unauthorized",
                        "message": "Authorization: Bearer 토큰이 필요합니다.",
                    }
                },
            )
        presented = auth[7:].strip()
        if not secrets.compare_digest(presented, self._token):
            return JSONResponse(
                status_code=401,
                content={
                    "error": {
                        "code": "unauthorized",
                        "message": "유효하지 않은 토큰입니다.",
                    }
                },
            )
        return await call_next(request)
