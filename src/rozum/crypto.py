"""Signature generation and strict verification for ROZUM profiles."""

from __future__ import annotations

import base64
import hashlib
import hmac
from collections.abc import Mapping
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from .canonical import build_signing_input
from .errors import ErrorCode, ProtocolViolation
from .keys import KeyRecord, SignatureProfile


def _strict_base64(value: str, expected_length: int) -> bytes:
    try:
        decoded = base64.b64decode(value, validate=True)
    except (ValueError, TypeError) as exc:
        raise ProtocolViolation(
            ErrorCode.SIGNATURE_FORMAT_INVALID,
            4,
            "Signature is not canonical RFC 4648 Base64",
        ) from exc
    if len(decoded) != expected_length:
        raise ProtocolViolation(
            ErrorCode.SIGNATURE_FORMAT_INVALID,
            4,
            f"Signature must decode to exactly {expected_length} bytes",
            details={"expected_bytes": expected_length, "actual_bytes": len(decoded)},
        )
    if base64.b64encode(decoded).decode("ascii") != value:
        raise ProtocolViolation(
            ErrorCode.SIGNATURE_FORMAT_INVALID,
            4,
            "Signature Base64 is not canonically padded",
        )
    return decoded


def verify_signature(envelope: Mapping[str, Any], record: KeyRecord | None) -> str:
    if record is None:
        raise ProtocolViolation(ErrorCode.KEY_NOT_FOUND, 4, "Verification key was not found")

    signature = envelope["signature"]
    if record.profile is SignatureProfile.UNSIGNED_MANUAL:
        if signature is not None:
            raise ProtocolViolation(
                ErrorCode.SIGNATURE_FORMAT_INVALID,
                4,
                "A preauthorized manual channel must use signature:null",
            )
        return "UNSIGNED_ALLOWED"

    if signature is None:
        raise ProtocolViolation(
            ErrorCode.SIGNATURE_REQUIRED,
            4,
            "This channel requires a cryptographic signature",
        )

    signing_input = build_signing_input(envelope)
    if record.profile is SignatureProfile.ED25519:
        raw_signature = _strict_base64(signature, 64)
        assert record.verification_key is not None
        public_key = Ed25519PublicKey.from_public_bytes(record.verification_key)
        try:
            public_key.verify(raw_signature, signing_input)
        except InvalidSignature as exc:
            raise ProtocolViolation(
                ErrorCode.SIGNATURE_VERIFICATION_FAILED,
                4,
                "Cryptographic verification failed",
            ) from exc
        return "VERIFIED"

    if record.profile is SignatureProfile.HMAC_SHA256:
        raw_mac = _strict_base64(signature, 32)
        assert record.verification_key is not None
        expected_mac = hmac.new(record.verification_key, signing_input, hashlib.sha256).digest()
        if not hmac.compare_digest(raw_mac, expected_mac):
            raise ProtocolViolation(
                ErrorCode.SIGNATURE_VERIFICATION_FAILED,
                4,
                "Cryptographic verification failed",
            )
        return "VERIFIED"

    raise ProtocolViolation(
        ErrorCode.SIGNATURE_FORMAT_INVALID,
        4,
        "Unsupported cryptographic profile",
    )


def sign_ed25519(envelope: Mapping[str, Any], private_seed: bytes) -> str:
    if len(private_seed) != 32:
        raise ValueError("Ed25519 private seed must be exactly 32 bytes")
    signature = Ed25519PrivateKey.from_private_bytes(private_seed).sign(
        build_signing_input(envelope)
    )
    return base64.b64encode(signature).decode("ascii")


def sign_hmac_sha256(envelope: Mapping[str, Any], secret: bytes) -> str:
    if not secret:
        raise ValueError("HMAC secret must be non-empty")
    mac = hmac.new(secret, build_signing_input(envelope), hashlib.sha256).digest()
    return base64.b64encode(mac).decode("ascii")
