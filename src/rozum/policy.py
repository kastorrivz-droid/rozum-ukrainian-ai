"""Explicit semantic policy for requirements left configurable by v2.1."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

import rfc8785

from .canonical import canonicalize_json
from .errors import ErrorCode, ProtocolViolation


DEFAULT_INTENTS = frozenset(
    {
        "argos_monitor",
        "inter_ai_task_request",
        "inter_ai_task_response",
        "inter_ai_task_result",
        "protocol_error",
        "system_architecture_analyze",
    }
)

DEFAULT_ROLES = frozenset(
    {"architect", "core", "orchestrator", "interface", "navigator", "system"}
)

DEFAULT_REPLY_REQUIRED_INTENTS = frozenset(
    {"inter_ai_task_response", "inter_ai_task_result", "protocol_error"}
)

FREE_SIGNED_SCALAR_PATHS = (
    ("sender_id",),
    ("key_id",),
    ("author", "id"),
    ("author", "role"),
    ("intent",),
    ("output_format",),
)


def _at_path(document: dict[str, Any], path: tuple[str, ...]) -> Any:
    value: Any = document
    for part in path:
        value = value[part]
    return value


def _is_uuid_v4(value: str) -> bool:
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError, TypeError):
        return False
    return parsed.version == 4 and str(parsed) == value


def parse_utc_timestamp(value: str) -> datetime:
    if not value.endswith("Z"):
        raise ValueError("timestamp must end in Z")
    parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ValueError("timestamp must be UTC")
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class ReceiverPolicy:
    max_age: timedelta = timedelta(minutes=5)
    max_future_skew: timedelta = timedelta(seconds=30)
    replay_ttl: timedelta = timedelta(minutes=6)
    allowed_intents: frozenset[str] = field(default_factory=lambda: DEFAULT_INTENTS)
    allowed_roles: frozenset[str] = field(default_factory=lambda: DEFAULT_ROLES)
    reply_required_intents: frozenset[str] = field(
        default_factory=lambda: DEFAULT_REPLY_REQUIRED_INTENTS
    )
    require_known_reply: bool = True
    forbid_colon_in_free_signed_scalars: bool = True

    def __post_init__(self) -> None:
        if self.max_age < timedelta(0) or self.max_future_skew < timedelta(0):
            raise ValueError("timestamp windows cannot be negative")
        if self.replay_ttl < self.max_age + self.max_future_skew:
            raise ValueError("replay_ttl must cover max_age plus max_future_skew")

    @classmethod
    def from_file(cls, path: str | Path) -> "ReceiverPolicy":
        document = json.loads(Path(path).read_text(encoding="utf-8"))
        timestamp = document["timestamp"]
        replay = document["replay"]
        return cls(
            max_age=timedelta(seconds=timestamp["max_age_seconds"]),
            max_future_skew=timedelta(seconds=timestamp["max_future_skew_seconds"]),
            replay_ttl=timedelta(seconds=replay["ttl_seconds"]),
            allowed_intents=frozenset(document["allowed_intents"]),
            allowed_roles=frozenset(document["allowed_roles"]),
            reply_required_intents=frozenset(
                document.get("reply_required_intents", DEFAULT_REPLY_REQUIRED_INTENTS)
            ),
            require_known_reply=document.get("require_known_reply", True),
            forbid_colon_in_free_signed_scalars=document.get(
                "forbid_colon_in_free_signed_scalars", True
            ),
        )

    def validate(self, envelope: dict[str, Any], now: datetime) -> None:
        if now.tzinfo is None:
            raise ValueError("receiver clock must be timezone-aware")
        now = now.astimezone(timezone.utc)
        try:
            timestamp = parse_utc_timestamp(envelope["timestamp"])
        except (ValueError, TypeError) as exc:
            raise ProtocolViolation(
                ErrorCode.SEMANTIC_INVALID,
                2,
                "Timestamp is not strict UTC RFC 3339",
            ) from exc

        if now - timestamp > self.max_age or timestamp - now > self.max_future_skew:
            raise ProtocolViolation(
                ErrorCode.TIMESTAMP_OUT_OF_WINDOW,
                2,
                "Timestamp is outside the configured acceptance window",
                retryable=True,
                details={
                    "max_age_seconds": int(self.max_age.total_seconds()),
                    "max_future_skew_seconds": int(self.max_future_skew.total_seconds()),
                },
            )

        if not _is_uuid_v4(envelope["id"]):
            raise ProtocolViolation(
                ErrorCode.SEMANTIC_INVALID,
                2,
                "id must be a canonical lowercase UUIDv4",
                details={"rule": "id_canonical_uuidv4"},
            )

        if envelope["intent"] not in self.allowed_intents:
            raise ProtocolViolation(
                ErrorCode.SEMANTIC_INVALID,
                2,
                "Intent is not present in the protocol policy allowlist",
                details={"rule": "intent_allowlist"},
            )
        if envelope["author"]["role"] not in self.allowed_roles:
            raise ProtocolViolation(
                ErrorCode.SEMANTIC_INVALID,
                2,
                "Author role is not present in the receiver vocabulary",
                details={"rule": "author_role_allowlist"},
            )

        reply_to = envelope["reply_to"]
        if envelope["intent"] in self.reply_required_intents and reply_to is None:
            raise ProtocolViolation(
                ErrorCode.SEMANTIC_INVALID,
                2,
                "This intent requires reply_to to reference the incoming message",
                details={"rule": "reply_to_required_for_intent"},
            )
        if reply_to is not None and not _is_uuid_v4(reply_to):
            raise ProtocolViolation(
                ErrorCode.SEMANTIC_INVALID,
                2,
                "reply_to must be a canonical lowercase UUIDv4",
                details={"rule": "reply_to_uuidv4"},
            )

        if self.forbid_colon_in_free_signed_scalars:
            for path in FREE_SIGNED_SCALAR_PATHS:
                if ":" in _at_path(envelope, path):
                    raise ProtocolViolation(
                        ErrorCode.SEMANTIC_INVALID,
                        2,
                        "Colon is forbidden in free signed scalar fields under the v2.1 safety policy",
                        details={"rule": "unescaped_colon", "path": ".".join(path)},
                    )

        try:
            for path in FREE_SIGNED_SCALAR_PATHS:
                _at_path(envelope, path).encode("utf-8", errors="strict")
            canonicalize_json(envelope["context"])
            canonicalize_json(envelope["data"])
            envelope["question"].encode("utf-8", errors="strict")
        except (rfc8785.CanonicalizationError, UnicodeEncodeError) as exc:
            raise ProtocolViolation(
                ErrorCode.SEMANTIC_INVALID,
                2,
                "Message content is outside the RFC 8785/I-JSON domain",
                details={"rule": "jcs_domain"},
            ) from exc
