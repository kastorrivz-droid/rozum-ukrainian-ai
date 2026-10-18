from __future__ import annotations

import asyncio
import unittest
from datetime import datetime, timezone

from fastapi import Request
from fastapi.testclient import TestClient

from rozum.http_api import (
    TransportErrorCode,
    TransportFailure,
    _read_limited_body,
    _validate_request_headers,
    create_app,
)
from rozum.keys import KeyRecord, KeyRegistry, SignatureProfile
from rozum.protocol_errors import ReceiverIdentity
from rozum.receiver import Receiver
from rozum.replay import InMemoryReplayStore
from rozum.schema import SchemaValidator

from .common import cvt_now, hmac_envelope


SECRET = b"http-integration-test-key"


def _receiver() -> Receiver:
    registry = KeyRegistry(
        [
            KeyRecord(
                "sender_hmac",
                "hmac-v1",
                SignatureProfile.HMAC_SHA256,
                SECRET,
            )
        ]
    )
    return Receiver(registry, clock=cvt_now)


class HTTPReceiverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app(
            _receiver(),
            ReceiverIdentity("argos_receiver", "manual-errors-v1"),
            max_body_bytes=8_192,
            body_timeout_seconds=1.0,
        )
        self.client = TestClient(self.app, raise_server_exceptions=False)

    def tearDown(self) -> None:
        self.client.close()

    def test_health_and_readiness_do_not_expose_configuration(self) -> None:
        health = self.client.get("/healthz")
        ready = self.client.get("/readyz")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json(), {"status": "ok"})
        self.assertEqual(ready.status_code, 200)
        self.assertEqual(ready.json()["protocol_version"], "2.1")
        self.assertIn("runtime_version", ready.json())

    def test_readiness_fails_closed_when_replay_store_is_unavailable(self) -> None:
        class UnreadyReplayStore(InMemoryReplayStore):
            def check_ready(self) -> bool:
                return False

        receiver = _receiver()
        receiver.replay_store = UnreadyReplayStore()
        app = create_app(
            receiver,
            ReceiverIdentity("argos_receiver", "manual-errors-v1"),
        )
        with TestClient(app) as client:
            response = client.get("/readyz")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["status"], "not_ready")

    def test_valid_signed_message_is_accepted(self) -> None:
        envelope = hmac_envelope(secret=SECRET)
        response = self.client.post("/v1/messages", json=envelope)
        self.assertEqual(response.status_code, 202)
        self.assertTrue(response.json()["accepted"])
        self.assertEqual(response.json()["message_id"], envelope["id"])
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")

    def test_replay_is_a_conflict_with_schema_valid_protocol_error(self) -> None:
        envelope = hmac_envelope(secret=SECRET)
        self.assertEqual(self.client.post("/v1/messages", json=envelope).status_code, 202)
        response = self.client.post("/v1/messages", json=envelope)
        self.assertEqual(response.status_code, 409)
        payload = response.json()
        SchemaValidator().validate(payload)
        self.assertEqual(payload["reply_to"], envelope["id"])
        self.assertEqual(payload["data"]["error"]["code"], "REPLAY_CONFLICT")

    def test_bad_signature_is_an_authentication_failure(self) -> None:
        envelope = hmac_envelope(secret=SECRET)
        envelope["question"] = "tampered after signing"
        response = self.client.post("/v1/messages", json=envelope)
        self.assertEqual(response.status_code, 401)
        payload = response.json()
        SchemaValidator().validate(payload)
        self.assertEqual(
            payload["data"]["error"]["code"],
            "SIGNATURE_VERIFICATION_FAILED",
        )
        self.assertEqual(payload["data"]["error"]["details"], {})

    def test_schema_failure_with_safe_ids_is_correlated(self) -> None:
        envelope = hmac_envelope(secret=SECRET)
        del envelope["author"]
        response = self.client.post("/v1/messages", json=envelope)
        self.assertEqual(response.status_code, 422)
        payload = response.json()
        SchemaValidator().validate(payload)
        self.assertEqual(payload["reply_to"], envelope["id"])
        self.assertEqual(payload["data"]["error"]["code"], "SCHEMA_INVALID")

    def test_schema_failure_without_safe_ids_is_not_correlated(self) -> None:
        response = self.client.post("/v1/messages", json={})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["kind"], "transport_error")
        self.assertEqual(response.json()["correlation"]["reply_to"], None)

    def test_malformed_duplicate_and_nonstandard_json_are_rejected(self) -> None:
        cases = (
            (b"{", "MALFORMED_JSON"),
            (b'{"a":1,"a":2}', "DUPLICATE_JSON_KEY"),
            (b'{"value":NaN}', "MALFORMED_JSON"),
            (b"\xef\xbb\xbf{}", "MALFORMED_JSON"),
            (b'{"value":"\xff"}', "MALFORMED_JSON"),
            (b'{"value":"\\ud800"}', "MALFORMED_JSON"),
        )
        for body, expected_code in cases:
            with self.subTest(expected_code=expected_code, body=body):
                response = self.client.post(
                    "/v1/messages",
                    content=body,
                    headers={"content-type": "application/json"},
                )
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["error"]["code"], expected_code)

    def test_media_type_charset_and_content_encoding_are_enforced(self) -> None:
        envelope = hmac_envelope(secret=SECRET)
        cases = (
            ({"content-type": "text/plain"}, "UNSUPPORTED_MEDIA_TYPE"),
            (
                {"content-type": "application/json; charset=iso-8859-1"},
                "UNSUPPORTED_MEDIA_TYPE",
            ),
            (
                {"content-type": "application/json", "content-encoding": "gzip"},
                "UNSUPPORTED_CONTENT_ENCODING",
            ),
        )
        for headers, expected_code in cases:
            with self.subTest(headers=headers):
                response = self.client.post(
                    "/v1/messages",
                    content=str(envelope),
                    headers=headers,
                )
                self.assertEqual(response.status_code, 415)
                self.assertEqual(response.json()["error"]["code"], expected_code)

    def test_declared_and_actual_body_limits_are_enforced(self) -> None:
        small_app = create_app(
            _receiver(),
            ReceiverIdentity("argos_receiver", "manual-errors-v1"),
            max_body_bytes=32,
        )
        with TestClient(small_app) as client:
            response = client.post(
                "/v1/messages",
                content=b'{' + (b'"padding":"' + b"x" * 64 + b'"}'),
                headers={"content-type": "application/json", "content-length": "1"},
            )
            self.assertEqual(response.status_code, 413)
            self.assertEqual(response.json()["error"]["code"], "PAYLOAD_TOO_LARGE")

            response = client.post(
                "/v1/messages",
                content=b"{}",
                headers={
                    "content-type": "application/json",
                    "content-length": "1000",
                },
            )
            self.assertEqual(response.status_code, 413)

    def test_internal_exception_is_not_reflected_to_the_client(self) -> None:
        class BrokenReceiver:
            @staticmethod
            def clock() -> datetime:
                return datetime.now(timezone.utc)

            @staticmethod
            def process(*args, **kwargs):  # type: ignore[no-untyped-def]
                raise RuntimeError("private-internal-value")

        app = create_app(  # type: ignore[arg-type]
            BrokenReceiver(),
            ReceiverIdentity("argos_receiver", "manual-errors-v1"),
        )
        with self.assertLogs("rozum.http_api", level="ERROR") as captured:
            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.post(
                    "/v1/messages",
                    json=hmac_envelope(secret=SECRET),
                )
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["error"]["code"], "INTERNAL_ERROR")
        self.assertNotIn("private-internal-value", response.text)
        self.assertNotIn("private-internal-value", "\n".join(captured.output))


class BodyDeadlineTests(unittest.TestCase):
    def test_content_length_accepts_ascii_decimal_only(self) -> None:
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/messages",
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", b"+1"),
            ],
        }
        request = Request(scope)
        with self.assertRaises(TransportFailure) as captured:
            _validate_request_headers(request, 100)
        self.assertEqual(
            captured.exception.code,
            TransportErrorCode.INVALID_CONTENT_LENGTH,
        )

    def test_slow_body_hits_deadline(self) -> None:
        sent = False

        async def receive():  # type: ignore[no-untyped-def]
            nonlocal sent
            await asyncio.sleep(0.02)
            if not sent:
                sent = True
                return {"type": "http.request", "body": b"{}", "more_body": False}
            return {"type": "http.disconnect"}

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/v1/messages",
            "raw_path": b"/v1/messages",
            "query_string": b"",
            "headers": [(b"content-type", b"application/json")],
            "client": ("test", 1),
            "server": ("testserver", 80),
        }
        request = Request(scope, receive)
        with self.assertRaises(TransportFailure) as captured:
            asyncio.run(
                _read_limited_body(
                    request,
                    max_body_bytes=100,
                    timeout_seconds=0.001,
                )
            )
        self.assertEqual(captured.exception.code, TransportErrorCode.REQUEST_TIMEOUT)


if __name__ == "__main__":
    unittest.main()
