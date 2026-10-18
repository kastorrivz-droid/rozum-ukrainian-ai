"""Schema-valid protocol errors and safe outer transport failures."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from .errors import ProtocolViolation


@dataclass(frozen=True)
class ReceiverIdentity:
    sender_id: str
    key_id: str

    def __post_init__(self) -> None:
        if not self.sender_id.strip() or not self.key_id.strip():
            raise ValueError("receiver sender_id and key_id must be non-empty")
        if ":" in self.sender_id or ":" in self.key_id:
            raise ValueError("receiver sender_id and key_id must not contain ':'")


def _canonical_uuid_v4(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = UUID(value)
    except ValueError:
        return None
    if parsed.version != 4 or str(parsed) != value:
        return None
    return str(parsed)


def _safe_session_id(incoming: Any) -> str | None:
    if not isinstance(incoming, Mapping):
        return None
    context = incoming.get("context")
    if not isinstance(context, Mapping):
        return None
    session_id = context.get("session_id")
    return session_id if isinstance(session_id, str) and session_id else None


def build_error_response(
    violation: ProtocolViolation,
    incoming: Any,
    identity: ReceiverIdentity,
    *,
    now: datetime | None = None,
    include_details: bool = False,
) -> dict[str, Any]:
    """Return a protocol envelope when correlation is safe, otherwise an outer error."""

    reply_to = _canonical_uuid_v4(incoming.get("id")) if isinstance(incoming, Mapping) else None
    session_id = _safe_session_id(incoming)
    error_data = violation.as_dict()
    if not include_details:
        error_data["details"] = {}

    if reply_to is None or session_id is None:
        return {
            "kind": "transport_error",
            "error": error_data,
            "correlation": {"reply_to": None, "session_id": None},
        }

    timestamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return {
        "protocol": "ROZUM_AI_v2",
        "protocol_version": "2.1",
        "id": str(uuid4()),
        "timestamp": timestamp.isoformat(timespec="microseconds").replace("+00:00", "Z"),
        "sender_id": identity.sender_id,
        "key_id": identity.key_id,
        "author": {"id": identity.sender_id, "role": "system"},
        "intent": "protocol_error",
        "reply_to": reply_to,
        "context": {"session_id": session_id, "state": {"accepted": False}},
        "data": {"error": error_data},
        "question": "",
        "output_format": "protocol",
        "signature": None,
    }
