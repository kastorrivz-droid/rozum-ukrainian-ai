"""Protocol error types and machine-readable pipeline traces."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    SCHEMA_INVALID = "SCHEMA_INVALID"
    UNSUPPORTED_PROTOCOL_VERSION = "UNSUPPORTED_PROTOCOL_VERSION"
    SEMANTIC_INVALID = "SEMANTIC_INVALID"
    TIMESTAMP_OUT_OF_WINDOW = "TIMESTAMP_OUT_OF_WINDOW"
    SENDER_KEY_MISMATCH = "SENDER_KEY_MISMATCH"
    REPLAY_SUSPECTED = "REPLAY_SUSPECTED"
    SIGNATURE_REQUIRED = "SIGNATURE_REQUIRED"
    KEY_NOT_FOUND = "KEY_NOT_FOUND"
    SIGNATURE_FORMAT_INVALID = "SIGNATURE_FORMAT_INVALID"
    SIGNATURE_VERIFICATION_FAILED = "SIGNATURE_VERIFICATION_FAILED"
    REPLAY_CONFLICT = "REPLAY_CONFLICT"
    INTENT_NOT_SUPPORTED = "INTENT_NOT_SUPPORTED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ProtocolViolation(Exception):
    """A controlled rejection defined by 09_ERROR_PROTOCOL.md."""

    def __init__(
        self,
        code: ErrorCode,
        stage: int | str,
        message: str,
        *,
        retryable: bool = False,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.stage = stage
        self.message = message
        self.retryable = retryable
        self.details = details or {}

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code.value,
            "stage": self.stage,
            "retryable": self.retryable,
            "message": self.message,
            "details": self.details,
        }


@dataclass(frozen=True)
class TraceEntry:
    stage: int
    name: str
    status: str
    checks: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "stage": self.stage,
            "name": self.name,
            "status": self.status,
        }
        if self.checks:
            result["checks"] = list(self.checks)
        return result


@dataclass(frozen=True)
class ProcessResult:
    accepted: bool
    state: str
    crypto_status: str | None
    trace: tuple[TraceEntry, ...] = field(default_factory=tuple)
    error: ProtocolViolation | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "state": self.state,
            "crypto_status": self.crypto_status,
            "trace": [entry.as_dict() for entry in self.trace],
            "error": self.error.as_dict() if self.error else None,
        }
