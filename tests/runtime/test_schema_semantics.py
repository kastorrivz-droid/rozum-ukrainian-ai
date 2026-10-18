from __future__ import annotations

import copy
import unittest
from datetime import timedelta

from rozum.errors import ErrorCode
from rozum.receiver import Receiver

from .common import cvt_now, cvt_registry, load_json, manual_envelope, manual_registry


class SchemaAndSemanticTests(unittest.TestCase):
    def assert_rejected(self, envelope, code: ErrorCode):
        result = Receiver(cvt_registry()).process(envelope, now=cvt_now())
        self.assertFalse(result.accepted)
        self.assertIsNotNone(result.error)
        self.assertEqual(result.error.code, code)
        return result

    def test_missing_required_field_is_schema_invalid(self) -> None:
        envelope = load_json("envelope.signed.json")
        del envelope["data"]
        self.assert_rejected(envelope, ErrorCode.SCHEMA_INVALID)

    def test_extra_top_level_field_is_schema_invalid(self) -> None:
        envelope = load_json("envelope.signed.json")
        envelope["unexpected"] = True
        self.assert_rejected(envelope, ErrorCode.SCHEMA_INVALID)

    def test_unknown_version_is_not_silently_treated_as_21(self) -> None:
        envelope = load_json("envelope.signed.json")
        envelope["protocol_version"] = "2.2"
        self.assert_rejected(envelope, ErrorCode.UNSUPPORTED_PROTOCOL_VERSION)

    def test_timestamp_without_z_is_schema_invalid(self) -> None:
        envelope = load_json("envelope.signed.json")
        envelope["timestamp"] = "2026-08-22T08:50:00+00:00"
        self.assert_rejected(envelope, ErrorCode.SCHEMA_INVALID)

    def test_invalid_calendar_timestamp_is_schema_invalid(self) -> None:
        envelope = load_json("envelope.signed.json")
        envelope["timestamp"] = "2026-13-40T25:61:61Z"
        self.assert_rejected(envelope, ErrorCode.SCHEMA_INVALID)

    def test_invalid_base64_syntax_is_schema_invalid(self) -> None:
        envelope = load_json("envelope.signed.json")
        envelope["signature"] = "not_base64!"
        self.assert_rejected(envelope, ErrorCode.SCHEMA_INVALID)

    def test_uppercase_id_is_rejected_by_canonical_policy(self) -> None:
        envelope = load_json("envelope.signed.json")
        envelope["id"] = envelope["id"].upper()
        result = self.assert_rejected(envelope, ErrorCode.SEMANTIC_INVALID)
        self.assertEqual(result.error.details["rule"], "id_canonical_uuidv4")

    def test_non_v4_reply_to_is_rejected_semantically(self) -> None:
        envelope = load_json("envelope.signed.json")
        envelope["reply_to"] = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
        result = self.assert_rejected(envelope, ErrorCode.SEMANTIC_INVALID)
        self.assertEqual(result.error.details["rule"], "reply_to_uuidv4")

    def test_unknown_intent_is_rejected_by_policy(self) -> None:
        envelope = load_json("envelope.signed.json")
        envelope["intent"] = "invented_route"
        result = self.assert_rejected(envelope, ErrorCode.SEMANTIC_INVALID)
        self.assertEqual(result.error.details["rule"], "intent_allowlist")

    def test_sender_key_mismatch_is_rejected_before_crypto(self) -> None:
        envelope = load_json("envelope.signed.json")
        envelope["sender_id"] = "different_sender"
        self.assert_rejected(envelope, ErrorCode.SENDER_KEY_MISMATCH)

    def test_unknown_key_reaches_key_not_found_at_stage_four(self) -> None:
        envelope = load_json("envelope.signed.json")
        envelope["key_id"] = "unknown-key"
        result = self.assert_rejected(envelope, ErrorCode.KEY_NOT_FOUND)
        self.assertEqual(result.error.stage, 4)

    def test_colon_ambiguity_is_blocked_for_free_scalar_fields(self) -> None:
        envelope = load_json("envelope.signed.json")
        envelope["author"]["id"] = "human:vladislav"
        result = self.assert_rejected(envelope, ErrorCode.SEMANTIC_INVALID)
        self.assertEqual(result.error.details["rule"], "unescaped_colon")

    def test_number_outside_jcs_domain_is_rejected_semantically(self) -> None:
        envelope = load_json("envelope.signed.json")
        envelope["data"] = {"unsafe_integer": 2**60}
        result = self.assert_rejected(envelope, ErrorCode.SEMANTIC_INVALID)
        self.assertEqual(result.error.details["rule"], "jcs_domain")

    def test_lone_surrogate_in_signed_scalar_is_rejected_semantically(self) -> None:
        envelope = load_json("envelope.signed.json")
        envelope["sender_id"] = "invalid-\ud800"
        result = self.assert_rejected(envelope, ErrorCode.SEMANTIC_INVALID)
        self.assertEqual(result.error.details["rule"], "jcs_domain")

    def test_timestamp_boundaries_are_inclusive(self) -> None:
        now = cvt_now()
        receiver = Receiver(manual_registry())

        old_boundary = manual_envelope(
            timestamp=(now - timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
        )
        self.assertTrue(receiver.process(old_boundary, now=now).accepted)

        future_boundary = manual_envelope(
            timestamp=(now + timedelta(seconds=30)).isoformat().replace("+00:00", "Z")
        )
        self.assertTrue(receiver.process(future_boundary, now=now).accepted)

    def test_timestamp_outside_either_boundary_is_rejected(self) -> None:
        now = cvt_now()
        for timestamp in (
            now - timedelta(minutes=5, microseconds=1),
            now + timedelta(seconds=30, microseconds=1),
        ):
            with self.subTest(timestamp=timestamp):
                envelope = manual_envelope(
                    timestamp=timestamp.isoformat().replace("+00:00", "Z")
                )
                result = Receiver(manual_registry()).process(envelope, now=now)
                self.assertEqual(result.error.code, ErrorCode.TIMESTAMP_OUT_OF_WINDOW)
                self.assertTrue(result.error.retryable)

    def test_signature_failure_does_not_hide_earlier_semantic_failure(self) -> None:
        envelope = copy.deepcopy(load_json("negative_cases/tampered_envelope.json"))
        envelope["author"]["role"] = "unknown-role"
        result = self.assert_rejected(envelope, ErrorCode.SEMANTIC_INVALID)
        self.assertEqual([entry.stage for entry in result.trace], [1, 2])


if __name__ == "__main__":
    unittest.main()
