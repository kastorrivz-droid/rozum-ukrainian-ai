"""Security-bounded HTTP transport for the ROZUM_AI_v2.1 receiver."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import timezone
from enum import StrEnum
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.requests import ClientDisconnect

from . import __version__
from .errors import ErrorCode, ProtocolViolation
from .protocol_errors import ReceiverIdentity, build_error_response
from .receiver import Receiver


LOGGER = logging.getLogger(__name__)

DEFAULT_MAX_BODY_BYTES = 1_048_576
DEFAULT_BODY_TIMEOUT_SECONDS = 10.0

SECURITY_HEADERS = {
    "Cache-Control": "no-store",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-ROZUM-Protocol-Version": "2.1",
}


class TransportErrorCode(StrEnum):
    """Non-normative errors emitted before a protocol envelope is available."""

    CLIENT_DISCONNECTED = "CLIENT_DISCONNECTED"
    DUPLICATE_JSON_KEY = "DUPLICATE_JSON_KEY"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    INVALID_CONTENT_LENGTH = "INVALID_CONTENT_LENGTH"
    MALFORMED_JSON = "MALFORMED_JSON"
    PAYLOAD_TOO_LARGE = "PAYLOAD_TOO_LARGE"
    REQUEST_TIMEOUT = "REQUEST_TIMEOUT"
    UNSUPPORTED_CONTENT_ENCODING = "UNSUPPORTED_CONTENT_ENCODING"
    UNSUPPORTED_MEDIA_TYPE = "UNSUPPORTED_MEDIA_TYPE"


class TransportFailure(Exception):
    def __init__(
        self,
        code: TransportErrorCode,
        status_code: int,
        message: str,
        *,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.message = message
        self.retryable = retryable


class _DuplicateJSONKey(ValueError):
    pass


def _transport_response(failure: TransportFailure) -> JSONResponse:
    return JSONResponse(
        status_code=failure.status_code,
        content={
            "kind": "transport_error",
            "error": {
                "code": failure.code.value,
                "stage": "transport",
                "retryable": failure.retryable,
                "message": failure.message,
                "details": {},
            },
            "correlation": {"reply_to": None, "session_id": None},
        },
    )


def _validate_request_headers(request: Request, max_body_bytes: int) -> None:
    content_type = request.headers.get("content-type")
    media_type = content_type.split(";", 1)[0].strip().lower() if content_type else ""
    if media_type != "application/json":
        raise TransportFailure(
            TransportErrorCode.UNSUPPORTED_MEDIA_TYPE,
            415,
            "Content-Type must be application/json",
        )

    if content_type and ";" in content_type:
        for parameter in content_type.split(";")[1:]:
            name, separator, value = parameter.strip().partition("=")
            if (
                separator
                and name.strip().lower() == "charset"
                and value.strip().strip('"').lower() not in {"utf-8", "utf8"}
            ):
                raise TransportFailure(
                    TransportErrorCode.UNSUPPORTED_MEDIA_TYPE,
                    415,
                    "JSON request bodies must use UTF-8",
                )

    content_encoding = (
        request.headers.get("content-encoding", "identity").strip().lower()
    )
    if content_encoding not in {"", "identity"}:
        raise TransportFailure(
            TransportErrorCode.UNSUPPORTED_CONTENT_ENCODING,
            415,
            "Compressed request bodies are not accepted",
        )

    content_length = request.headers.get("content-length")
    if content_length is None:
        return
    if not content_length or any(
        character < "0" or character > "9" for character in content_length
    ):
        raise TransportFailure(
            TransportErrorCode.INVALID_CONTENT_LENGTH,
            400,
            "Content-Length must be a non-negative decimal integer",
        )
    declared_length = int(content_length, 10)
    if declared_length > max_body_bytes:
        raise TransportFailure(
            TransportErrorCode.PAYLOAD_TOO_LARGE,
            413,
            "Request body exceeds the configured byte limit",
        )


async def _read_limited_body(
    request: Request,
    *,
    max_body_bytes: int,
    timeout_seconds: float,
) -> bytes:
    body = bytearray()
    try:
        async with asyncio.timeout(timeout_seconds):
            async for chunk in request.stream():
                if len(body) + len(chunk) > max_body_bytes:
                    raise TransportFailure(
                        TransportErrorCode.PAYLOAD_TOO_LARGE,
                        413,
                        "Request body exceeds the configured byte limit",
                    )
                body.extend(chunk)
    except TimeoutError as exc:
        raise TransportFailure(
            TransportErrorCode.REQUEST_TIMEOUT,
            408,
            "Request body was not received before the configured deadline",
            retryable=True,
        ) from exc
    except ClientDisconnect as exc:
        raise TransportFailure(
            TransportErrorCode.CLIENT_DISCONNECTED,
            408,
            "Client disconnected before the request body was complete",
            retryable=True,
        ) from exc
    return bytes(body)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJSONKey
        result[key] = value
    return result


def _reject_nonstandard_number(_: str) -> None:
    raise ValueError("non-standard JSON number")


def _decode_json(body: bytes) -> Any:
    if body.startswith(b"\xef\xbb\xbf"):
        raise TransportFailure(
            TransportErrorCode.MALFORMED_JSON,
            400,
            "Request body is not strict UTF-8 JSON",
        )
    try:
        text = body.decode("utf-8", errors="strict")
        value = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_nonstandard_number,
        )
        _validate_unicode_tree(value)
        return value
    except _DuplicateJSONKey as exc:
        raise TransportFailure(
            TransportErrorCode.DUPLICATE_JSON_KEY,
            400,
            "JSON objects must not contain duplicate member names",
        ) from exc
    except (
        UnicodeDecodeError,
        UnicodeEncodeError,
        json.JSONDecodeError,
        ValueError,
        RecursionError,
    ) as exc:
        raise TransportFailure(
            TransportErrorCode.MALFORMED_JSON,
            400,
            "Request body is not strict UTF-8 JSON",
        ) from exc


def _validate_unicode_tree(value: Any) -> None:
    if isinstance(value, str):
        value.encode("utf-8", errors="strict")
    elif isinstance(value, list):
        for item in value:
            _validate_unicode_tree(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            key.encode("utf-8", errors="strict")
            _validate_unicode_tree(item)


_AUTHENTICATION_ERRORS = {
    ErrorCode.KEY_NOT_FOUND,
    ErrorCode.SENDER_KEY_MISMATCH,
    ErrorCode.SIGNATURE_FORMAT_INVALID,
    ErrorCode.SIGNATURE_REQUIRED,
    ErrorCode.SIGNATURE_VERIFICATION_FAILED,
}
_REPLAY_ERRORS = {ErrorCode.REPLAY_CONFLICT, ErrorCode.REPLAY_SUSPECTED}


def status_for_violation(violation: ProtocolViolation) -> int:
    if violation.code in _AUTHENTICATION_ERRORS:
        return 401
    if violation.code in _REPLAY_ERRORS:
        return 409
    if violation.code is ErrorCode.INTERNAL_ERROR:
        return 500
    return 422


def create_app(
    receiver: Receiver,
    identity: ReceiverIdentity,
    *,
    max_body_bytes: int = DEFAULT_MAX_BODY_BYTES,
    body_timeout_seconds: float = DEFAULT_BODY_TIMEOUT_SECONDS,
) -> FastAPI:
    """Create a single-receiver ASGI app without documentation endpoints."""

    if max_body_bytes < 1:
        raise ValueError("max_body_bytes must be positive")
    if body_timeout_seconds <= 0:
        raise ValueError("body_timeout_seconds must be positive")

    app = FastAPI(
        title="ROZUM_AI_v2.1 receiver",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):  # type: ignore[no-untyped-def]
        response = await call_next(request)
        for name, value in SECURITY_HEADERS.items():
            response.headers[name] = value
        return response

    @app.get("/healthz", include_in_schema=False)
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz", include_in_schema=False)
    async def ready() -> JSONResponse:
        try:
            replay_ready = await asyncio.to_thread(receiver.replay_store.check_ready)
        except Exception as exc:
            LOGGER.error("Readiness check failed (%s)", type(exc).__name__)
            replay_ready = False
        return JSONResponse(
            status_code=200 if replay_ready else 503,
            content={
                "status": "ready" if replay_ready else "not_ready",
                "protocol": "ROZUM_AI_v2",
                "protocol_version": "2.1",
                "runtime_version": __version__,
            },
        )

    @app.post("/v1/messages", include_in_schema=False)
    async def receive_message(request: Request) -> JSONResponse:
        try:
            _validate_request_headers(request, max_body_bytes)
            body = await _read_limited_body(
                request,
                max_body_bytes=max_body_bytes,
                timeout_seconds=body_timeout_seconds,
            )
            envelope = _decode_json(body)
        except TransportFailure as failure:
            return _transport_response(failure)

        try:
            now = receiver.clock()
            if now.tzinfo is None:
                now = now.replace(tzinfo=timezone.utc)
            else:
                now = now.astimezone(timezone.utc)
            result = await asyncio.to_thread(receiver.process, envelope, now=now)
            if result.accepted:
                response = result.as_dict()
                response["message_id"] = envelope["id"]
                response["protocol_version"] = "2.1"
                return JSONResponse(status_code=202, content=response)

            if result.error is None:
                raise RuntimeError("rejected receiver result has no protocol error")
            response = build_error_response(result.error, envelope, identity, now=now)
            return JSONResponse(
                status_code=status_for_violation(result.error),
                content=response,
            )
        except Exception as exc:
            LOGGER.error("Receiver processing failed (%s)", type(exc).__name__)
            return _transport_response(
                TransportFailure(
                    TransportErrorCode.INTERNAL_ERROR,
                    500,
                    "Receiver could not complete the request",
                    retryable=True,
                )
            )

    return app
