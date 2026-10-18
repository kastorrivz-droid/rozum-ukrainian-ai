from __future__ import annotations

import unittest

from rozum.errors import ErrorCode
from rozum.keys import KeyRecord, KeyRegistry, SignatureProfile
from rozum.receiver import Receiver

from .common import cvt_now, hmac_envelope


class ThreadingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.request_key = b"test-only-request-key"
        self.response_key = b"test-only-response-key"
        self.registry = KeyRegistry(
            [
                KeyRecord(
                    "sender_hmac",
                    "hmac-v1",
                    SignatureProfile.HMAC_SHA256,
                    self.request_key,
                ),
                KeyRecord(
                    "andromeda_hmac",
                    "hmac-response-v1",
                    SignatureProfile.HMAC_SHA256,
                    self.response_key,
                ),
            ]
        )

    def test_response_uses_new_id_known_reply_and_same_session(self) -> None:
        receiver = Receiver(self.registry)
        request = hmac_envelope(secret=self.request_key, session_id="sess_thread")
        request_result = receiver.process(request, now=cvt_now())
        self.assertTrue(request_result.accepted)

        response = hmac_envelope(
            secret=self.response_key,
            sender_id="andromeda_hmac",
            key_id="hmac-response-v1",
            reply_to=request["id"],
            session_id="sess_thread",
        )
        response_result = receiver.process(response, now=cvt_now())
        self.assertTrue(response_result.accepted)
        self.assertNotEqual(response["id"], request["id"])

    def test_unknown_reply_is_rejected_before_crypto(self) -> None:
        response = hmac_envelope(
            secret=self.response_key,
            sender_id="andromeda_hmac",
            key_id="hmac-response-v1",
            reply_to="6ba7b810-9dad-41d1-80b4-00c04fd430c8",
            session_id="sess_thread",
        )
        result = Receiver(self.registry).process(response, now=cvt_now())
        self.assertEqual(result.error.code, ErrorCode.SEMANTIC_INVALID)
        self.assertEqual(result.error.details["rule"], "known_reply_to")

    def test_response_without_reply_to_is_rejected(self) -> None:
        response = hmac_envelope(
            secret=self.response_key,
            sender_id="andromeda_hmac",
            key_id="hmac-response-v1",
        )
        response["intent"] = "inter_ai_task_response"
        result = Receiver(self.registry).process(response, now=cvt_now())
        self.assertEqual(result.error.code, ErrorCode.SEMANTIC_INVALID)
        self.assertEqual(result.error.details["rule"], "reply_to_required_for_intent")

    def test_reply_session_mismatch_is_rejected(self) -> None:
        receiver = Receiver(self.registry)
        request = hmac_envelope(secret=self.request_key, session_id="sess_original")
        self.assertTrue(receiver.process(request, now=cvt_now()).accepted)

        response = hmac_envelope(
            secret=self.response_key,
            sender_id="andromeda_hmac",
            key_id="hmac-response-v1",
            reply_to=request["id"],
            session_id="sess_other",
        )
        result = receiver.process(response, now=cvt_now())
        self.assertEqual(result.error.code, ErrorCode.SEMANTIC_INVALID)
        self.assertEqual(result.error.details["rule"], "reply_session_match")


if __name__ == "__main__":
    unittest.main()
