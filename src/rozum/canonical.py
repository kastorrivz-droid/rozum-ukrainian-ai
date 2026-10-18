"""ROZUM_AI_v2.1 canonical signing bytes."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any

import rfc8785


def canonicalize_json(value: Any) -> bytes:
    """Return RFC 8785 JCS bytes without text normalization."""

    return rfc8785.dumps(value)


def sha256_hex(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def build_signing_input(envelope: Mapping[str, Any]) -> bytes:
    """Build the exact LOCKED v2.1 signing string.

    ``reply_to`` and ``message_type`` are intentionally absent because the
    normative 2.1 profile does not sign them. Callers must not use either
    field as an authorization input.
    """

    author = envelope["author"]
    fields = (
        "ROZUM_v2_SIG",
        envelope["protocol_version"],
        envelope["id"],
        envelope["timestamp"],
        envelope["sender_id"],
        envelope["key_id"],
        author["id"],
        author["role"],
        envelope["intent"],
        sha256_hex(canonicalize_json(envelope["context"])),
        sha256_hex(canonicalize_json(envelope["data"])),
        sha256_hex(envelope["question"].encode("utf-8")),
        envelope["output_format"],
    )
    return ":".join(fields).encode("utf-8")
