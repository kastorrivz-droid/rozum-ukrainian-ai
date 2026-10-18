from __future__ import annotations

import copy
import unittest

from rozum.canonical import build_signing_input
from rozum.crypto import sign_hmac_sha256
from rozum.errors import ErrorCode
from rozum.keys import KeyRecord, KeyRegistry, SignatureProfile
from rozum.receiver import Receiver

from .common import cvt_now, cvt_registry, hmac_envelope, load_json, manual_envelope, manual_registry


class CryptographicProfileTests(unittest.TestCase):
    def test_hmac_positive_and_rotation_vectors(self) -> None:
        key_v1 = b"test-only-hmac-key-v1"
        key_v2 = b"test-only-hmac-key-v2"
        registry = KeyRegistry(
            [
                KeyRecord("sender_hmac", "hmac-v1", SignatureProfile.HMAC_SHA256, key_v1),
                KeyRecord("sender_hmac", "hmac-v2", SignatureProfile.HMAC_SHA256, key_v2),
            ]
        )
        for key_id, secret in (("hmac-v1", key_v1), ("hmac-v2", key_v2)):
            with self.subTest(key_id=key_id):
                envelope = hmac_envelope(secret=secret, key_id=key_id)
                result = Receiver(registry).process(envelope, now=cvt_now())
                self.assertTrue(result.accepted)
                self.assertEqual(result.crypto_status, "VERIFIED")

    def test_wrong_hmac_is_rejected(self) -> None:
        envelope = hmac_envelope(secret=b"signing-key")
        registry = KeyRegistry(
            [
                KeyRecord(
                    "sender_hmac",
                    "hmac-v1",
                    SignatureProfile.HMAC_SHA256,
                    b"different-key",
                )
            ]
        )
        result = Receiver(registry).process(envelope, now=cvt_now())
        self.assertEqual(result.error.code, ErrorCode.SIGNATURE_VERIFICATION_FAILED)

    def test_unsigned_strict_channel_is_not_crypto_pass(self) -> None:
        envelope = load_json("envelope.unsigned.json")
        result = Receiver(cvt_registry()).process(envelope, now=cvt_now())
        self.assertFalse(result.accepted)
        self.assertEqual(result.error.code, ErrorCode.SIGNATURE_REQUIRED)

    def test_preauthorized_manual_channel_is_explicit(self) -> None:
        result = Receiver(manual_registry()).process(manual_envelope(), now=cvt_now())
        self.assertTrue(result.accepted)
        self.assertEqual(result.crypto_status, "UNSIGNED_ALLOWED")
        stage_four = next(entry for entry in result.trace if entry.stage == 4)
        self.assertEqual(stage_four.status, "UNSIGNED_ALLOWED")
        self.assertNotEqual(stage_four.status, "PASS")

    def test_der_signature_is_rejected_before_math(self) -> None:
        envelope = load_json("negative_cases/invalid_signature_format.json")
        result = Receiver(cvt_registry()).process(envelope, now=cvt_now())
        self.assertEqual(result.error.code, ErrorCode.SIGNATURE_FORMAT_INVALID)
        self.assertEqual(result.error.stage, 4)

    def test_tampered_payload_is_rejected(self) -> None:
        envelope = load_json("negative_cases/tampered_envelope.json")
        result = Receiver(cvt_registry()).process(envelope, now=cvt_now())
        self.assertEqual(result.error.code, ErrorCode.SIGNATURE_VERIFICATION_FAILED)

    def test_reply_to_and_message_type_are_characterized_as_unsigned_in_21(self) -> None:
        envelope = load_json("envelope.signed.json")
        baseline = build_signing_input(envelope)
        changed = copy.deepcopy(envelope)
        changed["reply_to"] = "6ba7b810-9dad-41d1-80b4-00c04fd430c8"
        changed["message_type"] = "do-not-authorize-from-this-field"
        self.assertEqual(build_signing_input(changed), baseline)

    def test_every_free_signed_scalar_changes_signing_bytes(self) -> None:
        baseline_envelope = load_json("envelope.unsigned.json")
        baseline = build_signing_input(baseline_envelope)
        mutations = {
            "sender_id": lambda value: value.__setitem__("sender_id", "changed_sender"),
            "key_id": lambda value: value.__setitem__("key_id", "changed-key"),
            "author.id": lambda value: value["author"].__setitem__("id", "changed_author"),
            "author.role": lambda value: value["author"].__setitem__("role", "navigator"),
            "intent": lambda value: value.__setitem__("intent", "inter_ai_task_result"),
            "output_format": lambda value: value.__setitem__("output_format", "json"),
        }
        for name, mutate in mutations.items():
            with self.subTest(field=name):
                changed = copy.deepcopy(baseline_envelope)
                mutate(changed)
                self.assertNotEqual(build_signing_input(changed), baseline)

    def test_hmac_signer_is_deterministic(self) -> None:
        envelope = hmac_envelope(secret=b"test-key")
        expected = envelope["signature"]
        envelope["signature"] = None
        self.assertEqual(sign_hmac_sha256(envelope, b"test-key"), expected)


if __name__ == "__main__":
    unittest.main()
