"""FastAPI application for the non-normative Reeves dialogue prototype."""

from __future__ import annotations

import asyncio
import json
import os
import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable, Iterable
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .models import ChatRequest, ChatResponse, GuardReport
from .provider import ChatProvider, detect_language, load_provider


DEFAULT_MAX_BODY_BYTES = 64 * 1024
DEFAULT_RATE_LIMIT = 30
DEFAULT_RATE_WINDOW_SECONDS = 60
DEFAULT_ALLOWED_ORIGINS = ("https://kastorrivz-droid.github.io",)

SECURITY_HEADERS = {
    "Cache-Control": "no-store",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-ROZUM-Assistant-Status": "PROPOSED",
}


class _DuplicateJSONKey(ValueError):
    pass


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJSONKey(key)
        result[key] = value
    return result


def _reject_nonstandard_number(value: str) -> None:
    raise ValueError(f"non-standard JSON number: {value}")


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
        headers=SECURITY_HEADERS,
    )


class BodyLimitMiddleware:
    """Read and replay the small chat body while enforcing an actual byte limit."""

    def __init__(self, app: ASGIApp, max_body_bytes: int) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("path") != "/v1/chat":
            await self.app(scope, receive, send)
            return

        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }
        if headers.get("content-encoding", "identity").lower() != "identity":
            response = _error_response(
                415,
                "UNSUPPORTED_CONTENT_ENCODING",
                "Compressed request bodies are not accepted.",
            )
            await response(scope, receive, send)
            return
        if "application/json" not in headers.get("content-type", "").lower():
            response = _error_response(
                415,
                "UNSUPPORTED_MEDIA_TYPE",
                "Content-Type must be application/json.",
            )
            await response(scope, receive, send)
            return

        messages: list[Message] = []
        total = 0
        more_body = True
        while more_body:
            message = await receive()
            messages.append(message)
            if message["type"] != "http.request":
                continue
            total += len(message.get("body", b""))
            if total > self.max_body_bytes:
                response = _error_response(
                    413,
                    "PAYLOAD_TOO_LARGE",
                    "Request body exceeds the configured limit.",
                )
                await response(scope, receive, send)
                return
            more_body = bool(message.get("more_body", False))

        body = b"".join(
            message.get("body", b"")
            for message in messages
            if message["type"] == "http.request"
        )
        try:
            json.loads(
                body.decode("utf-8"),
                object_pairs_hook=_reject_duplicate_keys,
                parse_constant=_reject_nonstandard_number,
            )
        except (UnicodeDecodeError, json.JSONDecodeError, _DuplicateJSONKey, ValueError):
            response = _error_response(
                400,
                "MALFORMED_JSON",
                "Body must be unambiguous UTF-8 JSON.",
            )
            await response(scope, receive, send)
            return

        index = 0

        async def replay() -> Message:
            nonlocal index
            if index < len(messages):
                message = messages[index]
                index += 1
                return message
            return {"type": "http.request", "body": b"", "more_body": False}

        await self.app(scope, replay, send)


class SlidingWindowRateLimiter:
    """Single-process beta limiter; production needs a shared durable limiter."""

    def __init__(self, limit: int, window_seconds: int) -> None:
        if limit < 1 or window_seconds < 1:
            raise ValueError("rate-limit values must be positive")
        self.limit = limit
        self.window_seconds = window_seconds
        self._events: defaultdict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def allow(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        async with self._lock:
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= self.limit:
                return False
            events.append(now)
            return True


def _origin_is_safe(origin: str) -> bool:
    parsed = urlparse(origin)
    if parsed.scheme == "https" and parsed.netloc:
        return True
    return parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost"}


def _allowed_origins_from_env() -> tuple[str, ...]:
    raw = os.getenv("REEVES_ALLOWED_ORIGINS", "")
    values = tuple(item.strip().rstrip("/") for item in raw.split(",") if item.strip())
    origins = values or DEFAULT_ALLOWED_ORIGINS
    if any(origin == "*" or not _origin_is_safe(origin) for origin in origins):
        raise RuntimeError("REEVES_ALLOWED_ORIGINS contains an unsafe origin")
    return origins


def create_app(
    provider: ChatProvider | None = None,
    *,
    allowed_origins: Iterable[str] | None = None,
    max_body_bytes: int = DEFAULT_MAX_BODY_BYTES,
    rate_limit: int = DEFAULT_RATE_LIMIT,
    rate_window_seconds: int = DEFAULT_RATE_WINDOW_SECONDS,
) -> FastAPI:
    selected_provider = provider or load_provider(os.getenv("REEVES_PROVIDER", "mock"))
    origins = tuple(allowed_origins or _allowed_origins_from_env())
    limiter = SlidingWindowRateLimiter(rate_limit, rate_window_seconds)

    app = FastAPI(
        title="Reeves API prototype",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.add_middleware(BodyLimitMiddleware, max_body_bytes=max_body_bytes)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
        max_age=600,
    )

    @app.middleware("http")
    async def security_headers(
        request: Request,
        call_next: Callable[[Request], Awaitable[Any]],
    ) -> Any:
        response = await call_next(request)
        for header, value in SECURITY_HEADERS.items():
            response.headers[header] = value
        return response

    @app.get("/healthz")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "reeves-api"}

    @app.get("/readyz")
    async def ready() -> dict[str, str]:
        return {
            "status": "ready",
            "service": "reeves-api",
            "provider": selected_provider.name,
            "validation_state": "PROPOSED",
        }

    @app.post("/v1/chat", response_model=ChatResponse)
    async def chat(payload: ChatRequest, request: Request) -> ChatResponse:
        client = request.client.host if request.client else "unknown"
        if not await limiter.allow(client):
            raise HTTPException(
                status_code=429,
                detail={"code": "RATE_LIMITED", "message": "Try again later."},
                headers={"Retry-After": str(rate_window_seconds)},
            )

        language = detect_language(payload)
        generated = await selected_provider.generate(payload, language)
        return ChatResponse(
            request_id=str(uuid4()),
            reply=generated.text,
            language=language,
            provider=selected_provider.name,
            citations=list(generated.citations),
            guard=GuardReport(
                checks=["schema", "body_limit", "rate_limit", "provider_allowlist"]
            ),
        )

    return app


app = create_app()
