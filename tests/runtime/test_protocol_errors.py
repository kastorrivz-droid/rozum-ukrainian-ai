from __future__ import annotations

import unittest
from datetime import datetime, timezone

from rozum.errors import ErrorCode, ProtocolViolation
from rozum.protocol_errors import ReceiverIdentity, build_error_response
from rozum.schema import SchemaValidator

from .common import load_json


class ErrorResponseTests(unittest.TestCase):
    def test_correlated_error_is_schema_valid(self) -> None:
        incoming = load_json("envelope.signed.json")
        violation = ProtocolViolation(
            ErrorCode.SIGNATURE_VERIFICATION_FAILED,
            4,
            "Cryptographic verification failed",
            details={"internal": "must-not-leak"},
        )
        response = build_error_response(
            violation,
            incoming,
            ReceiverIdentity("argos_receiver", "manual-channel"),
            now=datetime(2026, 9, 2, tzinfo=timezone.utc),
        )
        SchemaValidator().validate(response)
        self.assertEqual(response["reply_to"], incoming["id"])
        self.assertEqual(response["context"]["session_id"], incoming["context"]["session_id"])
        self.assertEqual(response["data"]["error"]["retryable"], False)
        self.assertEqual(response["data"]["error"]["details"], {})

    def test_untrusted_correlation_uses_outer_transport_error(self) -> None:
        violation = ProtocolViolation(ErrorCode.SCHEMA_INVALID, 1, "Invalid envelope")
        response = build_error_response(
            violation,
            {"id": "not-a-uuid", "context": {}},
            ReceiverIdentity("argos_receiver", "manual-channel"),
        )
        self.assertEqual(response["kind"], "transport_error")
        self.assertIsNone(response["correlation"]["reply_to"])
        self.assertIsNone(response["correlation"]["session_id"])


if __name__ == "__main__":
    unittest.main()
