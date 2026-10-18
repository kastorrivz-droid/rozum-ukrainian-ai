"""Trusted sender/key registry. The payload never selects its own algorithm."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any


class SignatureProfile(StrEnum):
    ED25519 = "ROZUM-SIG-ED25519"
    HMAC_SHA256 = "ROZUM-SIG-HMAC-SHA256"
    UNSIGNED_MANUAL = "ROZUM-UNSIGNED-MANUAL"


@dataclass(frozen=True)
class KeyRecord:
    sender_id: str
    key_id: str
    profile: SignatureProfile
    verification_key: bytes | None = None
    active: bool = True

    def __post_init__(self) -> None:
        if not self.sender_id or not self.key_id:
            raise ValueError("sender_id and key_id must be non-empty")
        if self.profile is SignatureProfile.ED25519:
            if self.verification_key is None or len(self.verification_key) != 32:
                raise ValueError("Ed25519 public key must be exactly 32 raw bytes")
        elif self.profile is SignatureProfile.HMAC_SHA256:
            if not self.verification_key:
                raise ValueError("HMAC key must be non-empty")
        elif self.verification_key is not None:
            raise ValueError("manual unsigned channels cannot carry key material")


class KeyRegistry:
    def __init__(self, records: list[KeyRecord] | tuple[KeyRecord, ...] = ()) -> None:
        self._records: dict[tuple[str, str], KeyRecord] = {}
        for record in records:
            self.add(record)

    def add(self, record: KeyRecord) -> None:
        key = (record.sender_id, record.key_id)
        if key in self._records:
            raise ValueError(f"duplicate registry entry for {key!r}")
        self._records[key] = record

    def resolve(self, sender_id: str, key_id: str) -> KeyRecord | None:
        record = self._records.get((sender_id, key_id))
        return record if record and record.active else None

    def owners_for_key_id(self, key_id: str) -> set[str]:
        return {
            sender_id
            for (sender_id, registered_key_id), record in self._records.items()
            if registered_key_id == key_id and record.active
        }

    @classmethod
    def from_file(cls, path: str | Path) -> "KeyRegistry":
        document = json.loads(Path(path).read_text(encoding="utf-8"))
        records = [cls._record_from_mapping(item) for item in document["keys"]]
        return cls(records)

    @staticmethod
    def _record_from_mapping(item: dict[str, Any]) -> KeyRecord:
        profile = SignatureProfile(item["profile"])
        key: bytes | None
        if profile is SignatureProfile.ED25519:
            key = bytes.fromhex(item["public_key_hex"])
        elif profile is SignatureProfile.HMAC_SHA256:
            environment_name = item["secret_env"]
            secret = os.environ.get(environment_name)
            if secret is None:
                raise ValueError(f"required HMAC environment variable is missing: {environment_name}")
            key = secret.encode("utf-8")
        else:
            key = None
        return KeyRecord(
            sender_id=item["sender_id"],
            key_id=item["key_id"],
            profile=profile,
            verification_key=key,
            active=item.get("active", True),
        )
