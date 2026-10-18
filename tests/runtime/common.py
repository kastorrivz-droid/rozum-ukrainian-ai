from __future__ import annotations

import copy
import json
from datetime import timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from rozum.crypto import sign_hmac_sha256
from rozum.keys import KeyRecord, KeyRegistry, SignatureProfile
from rozum.policy import parse_utc_timestamp


ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "tests/interoperability/CVT-001"
PUBLIC_KEY = bytes.fromhex(
    "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
)


def load_json(relative: str) -> dict[str, Any]:
    return json.loads((BUNDLE / relative).read_text(encoding="utf-8"))


def cvt_registry() -> KeyRegistry:
    return KeyRegistry(
        [
            KeyRecord(
                "agent_gemini_core",
                "key-v1",
                SignatureProfile.ED25519,
                PUBLIC_KEY,
            )
        ]
    )


def cvt_now():
    envelope = load_json("envelope.signed.json")
    return parse_utc_timestamp(envelope["timestamp"]) + timedelta(seconds=1)


def hmac_envelope(
    *,
    secret: bytes,
    sender_id: str = "sender_hmac",
    key_id: str = "hmac-v1",
    message_id: str | None = None,
    reply_to: str | None = None,
    session_id: str = "sess_hmac",
) -> dict[str, Any]:
    envelope: dict[str, Any] = {
        "protocol": "ROZUM_AI_v2",
        "protocol_version": "2.1",
        "id": message_id or str(uuid4()),
        "timestamp": "2026-08-22T08:50:00Z",
        "sender_id": sender_id,
        "key_id": key_id,
        "author": {"id": "human_vladislav", "role": "architect"},
        "intent": "inter_ai_task_request" if reply_to is None else "inter_ai_task_response",
        "reply_to": reply_to,
        "context": {"session_id": session_id, "state": {"step": 1}},
        "data": {"task": "runtime_test"},
        "question": "Проверить сообщение",
        "output_format": "protocol",
        "signature": None,
    }
    envelope["signature"] = sign_hmac_sha256(envelope, secret)
    return envelope


def manual_envelope(**updates: Any) -> dict[str, Any]:
    envelope = copy.deepcopy(load_json("envelope.unsigned.json"))
    envelope.update(
        {
            "id": str(uuid4()),
            "sender_id": "human_vladislav",
            "key_id": "manual-channel",
            "intent": "system_architecture_analyze",
        }
    )
    envelope.update(updates)
    return envelope


def manual_registry() -> KeyRegistry:
    return KeyRegistry(
        [
            KeyRecord(
                "human_vladislav",
                "manual-channel",
                SignatureProfile.UNSIGNED_MANUAL,
            )
        ]
    )
