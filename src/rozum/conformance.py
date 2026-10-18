"""Executable reproduction of the immutable CVT-001 evidence bundle."""

from __future__ import annotations

import hashlib
import json
import platform
from datetime import timedelta
from importlib.metadata import version
from pathlib import Path
from typing import Any

from .canonical import build_signing_input
from .crypto import sign_ed25519
from .errors import ErrorCode
from .keys import KeyRecord, KeyRegistry, SignatureProfile
from .policy import parse_utc_timestamp
from .receiver import Receiver


CVT001_PRIVATE_SEED_HEX = (
    "9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60"
)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _registry(bundle: Path) -> KeyRegistry:
    participant = _load_json(bundle / "participant_manifest.json")
    return KeyRegistry(
        [
            KeyRecord(
                sender_id=participant["sender_id"],
                key_id=participant["key_id"],
                profile=SignatureProfile(participant["cryptographic_profile"]),
                verification_key=bytes.fromhex(participant["public_key_hex"]),
            )
        ]
    )


def run_cvt001(bundle_path: str | Path) -> dict[str, Any]:
    bundle = Path(bundle_path)
    signed = _load_json(bundle / "envelope.signed.json")
    unsigned = _load_json(bundle / "envelope.unsigned.json")
    invalid_format = _load_json(bundle / "negative_cases/invalid_signature_format.json")
    tampered = _load_json(bundle / "negative_cases/tampered_envelope.json")
    expected_input = (bundle / "signing_input.bin").read_bytes()
    expected_digest = (bundle / "signing_input.sha256").read_text(encoding="ascii").strip()
    expected_signature = (bundle / "signature.b64").read_text(encoding="ascii").strip()
    now = parse_utc_timestamp(signed["timestamp"]) + timedelta(seconds=1)

    assertions: list[dict[str, str]] = []

    actual_input = build_signing_input(unsigned)
    assertion_1 = actual_input == expected_input and hashlib.sha256(actual_input).hexdigest() == expected_digest
    assertions.append(
        {
            "id": "CVT-001.1",
            "description": "JCS byte identity and canonical input digest",
            "status": "PASS" if assertion_1 else "FAIL",
        }
    )

    generated_signature = sign_ed25519(unsigned, bytes.fromhex(CVT001_PRIVATE_SEED_HEX))
    assertions.append(
        {
            "id": "CVT-001.2",
            "description": "Deterministic Ed25519 signature",
            "status": "PASS" if generated_signature == expected_signature else "FAIL",
        }
    )

    valid_result = Receiver(_registry(bundle)).process(signed, now=now)
    assertions.append(
        {
            "id": "CVT-001.3",
            "description": "Strict RAW-64 Ed25519 receiver acceptance",
            "status": "PASS" if valid_result.accepted else "FAIL",
        }
    )

    format_result = Receiver(_registry(bundle)).process(invalid_format, now=now)
    format_pass = (
        not format_result.accepted
        and format_result.error is not None
        and format_result.error.code is ErrorCode.SIGNATURE_FORMAT_INVALID
    )
    assertions.append(
        {
            "id": "CVT-001.4",
            "description": "Strict DER/non-64 signature rejection",
            "status": "PASS" if format_pass else "FAIL",
        }
    )

    replay_receiver = Receiver(_registry(bundle))
    first = replay_receiver.process(signed, now=now)
    duplicate = replay_receiver.process(signed, now=now)
    replay_pass = (
        first.accepted
        and not duplicate.accepted
        and duplicate.error is not None
        and duplicate.error.code is ErrorCode.REPLAY_CONFLICT
    )
    assertions.append(
        {
            "id": "CVT-001.5",
            "description": "Atomic replay commit and duplicate rejection",
            "status": "PASS" if replay_pass else "FAIL",
        }
    )

    tamper_result = Receiver(_registry(bundle)).process(tampered, now=now)
    tamper_pass = (
        not tamper_result.accepted
        and tamper_result.error is not None
        and tamper_result.error.code is ErrorCode.SIGNATURE_VERIFICATION_FAILED
    )
    assertions.append(
        {
            "id": "CVT-001.6",
            "description": "Signed payload mutation detection",
            "status": "PASS" if tamper_pass else "FAIL",
        }
    )

    overall = "PASS" if all(item["status"] == "PASS" for item in assertions) else "FAIL"
    return {
        "test_run_id": "CVT-001-runtime",
        "protocol_version_tested": "2.1",
        "environment": {
            "python": platform.python_version(),
            "cryptography": version("cryptography"),
            "jsonschema": version("jsonschema"),
            "rfc8785": version("rfc8785"),
        },
        "assertions": assertions,
        "overall_status": overall,
    }
