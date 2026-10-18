"""Executable receiver for the ROZUM_AI_v2.1 protocol."""

from .canonical import build_signing_input, sha256_hex
from .crypto import sign_ed25519, sign_hmac_sha256
from .keys import KeyRecord, KeyRegistry, SignatureProfile
from .policy import ReceiverPolicy
from .receiver import Receiver
from .replay import InMemoryReplayStore, SQLiteReplayStore

__all__ = [
    "InMemoryReplayStore",
    "KeyRecord",
    "KeyRegistry",
    "Receiver",
    "ReceiverPolicy",
    "SQLiteReplayStore",
    "SignatureProfile",
    "build_signing_input",
    "sha256_hex",
    "sign_ed25519",
    "sign_hmac_sha256",
]

__version__ = "0.2.0"
