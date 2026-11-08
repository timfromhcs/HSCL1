"""Local HTTP API (decision D6).

Loopback only (the launcher binds 127.0.0.1), no CORS at all, ``Host`` and ``Origin``
validated, a per-launch bearer token on every operation, bounded request bodies and
bounded concurrency. Operations run through an isolated worker (``run``), never in
this process.
"""

from __future__ import annotations

import hmac
import threading
from dataclasses import asdict
from typing import Any, Callable

import anyio.to_thread
import sympy as sp
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .. import __version__
from ..core.engine import OPERATIONS
from ..core.expression_ast import DEFAULT_LIMITS
from ..jobs.worker import run_isolated
from . import page

MAX_BODY_BYTES = 64 * 1024

_HTTP_FOR_STATUS = {
    "ok": 200,
    "partial": 200,
    "unresolved": 200,  # a valid computation without a closed form; the status field says so
    "invalid_input": 400,
    "unsupported": 501,
    "resource_limit": 422,
    "cancelled": 409,
    "engine_unavailable": 503,
    "internal_error": 500,
}


class ExpressionRequest(BaseModel):
    """Request body. Unknown fields are refused (``extra="forbid"``), never silently dropped."""

    model_config = ConfigDict(extra="forbid")

    expression: str = Field(max_length=DEFAULT_LIMITS.max_chars)
    variable: str = Field(max_length=16)
    #: Only the ``evaluate`` operation uses it; the engine refuses it for every other operation.
    value: str | None = Field(default=None, max_length=DEFAULT_LIMITS.max_chars)
    x_min: str | None = Field(default=None, max_length=DEFAULT_LIMITS.max_chars)
    x_max: str | None = Field(default=None, max_length=DEFAULT_LIMITS.max_chars)
    points: int | None = Field(default=None, strict=True)


class _BodyLimit:
    """Pure ASGI middleware: refuse bodies above ``MAX_BODY_BYTES`` with 413."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        declared = dict(scope["headers"]).get(b"content-length")
        if declared is not None and declared.isdigit() and int(declared) > MAX_BODY_BYTES:
            await self._refuse(send)
            return
        seen = 0

        async def counting_receive() -> dict:
            nonlocal seen
            message = await receive()
            if message["type"] == "http.request":
                seen += len(message.get("body", b""))
                if seen > MAX_BODY_BYTES:
                    raise _TooLarge()
            return message

        try:
            await self.app(scope, counting_receive, send)
        except _TooLarge:
            await self._refuse(send)

    @staticmethod
    async def _refuse(send: Callable) -> None:
        body = b'{"detail":"request body too large"}'
        await send({"type": "http.response.start", "status": 413,
                    "headers": [(b"content-type", b"application/json"),
                                (b"content-length", str(len(body)).encode())]})
        await send({"type": "http.response.body", "body": body})


class _TooLarge(Exception):
    pass


def create_app(
    *,
    token: str,
    port: int,
    run: Callable[[Any], dict[str, Any]] = run_isolated,
    max_concurrent: int = 2,
) -> FastAPI:
    if len(token) < 32:
        raise ValueError("token must be at least 32 characters")
    app = FastAPI(title="hcseasymath", version=__version__,
                  docs_url=None, redoc_url=None, openapi_url=None)
    origins = {f"http://127.0.0.1:{port}", f"http://localhost:{port}"}
    slots = threading.BoundedSemaphore(max_concurrent)

    @app.middleware("http")
    async def origin_check(request: Request, call_next: Callable) -> Any:
        origin = request.headers.get("origin")
        if origin is not None and origin not in origins:
            return JSONResponse({"detail": "origin not allowed"}, status_code=403)
        return await call_next(request)

    # Added after origin_check so they run first: Host, then body size.
    app.add_middleware(_BodyLimit)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])

    def require_token(authorization: str | None = Header(default=None)) -> None:
        scheme, _, value = (authorization or "").partition(" ")
        if scheme.lower() != "bearer" or not hmac.compare_digest(value.encode(), token.encode()):
            raise HTTPException(status_code=401, detail="missing or invalid token")

    @app.get("/")
    def index() -> HTMLResponse:
        return HTMLResponse(
            page.HTML,
            headers={
                "Content-Security-Policy": page.CSP,
                "X-Content-Type-Options": "nosniff",
                "Referrer-Policy": "no-referrer",
                "Cache-Control": "no-store",
            },
        )

    @app.get("/api/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "app": "hcseasymath", "version": __version__}

    @app.get("/api/v1/capabilities")
    def capabilities() -> dict[str, Any]:
        return {
            "operations": list(OPERATIONS),
            "engines": {"sympy": sp.__version__},
            "accelerators": {"hcsuda": "not_used"},
            "limits": asdict(DEFAULT_LIMITS),
        }

    def register(operation: str) -> None:
        @app.post(f"/api/v1/symbolic/{operation}", dependencies=[Depends(require_token)], name=operation)
        async def run_operation(body: ExpressionRequest) -> JSONResponse:
            if not slots.acquire(blocking=False):
                return JSONResponse({"detail": "busy, try again"}, status_code=429)
            try:
                request = {"operation": operation, **body.model_dump(exclude_none=True)}
                result = await anyio.to_thread.run_sync(run, request)
            finally:
                slots.release()
            return JSONResponse(result, status_code=_HTTP_FOR_STATUS.get(result.get("status"), 500))

    for operation in OPERATIONS:
        register(operation)

    return app
