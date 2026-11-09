from __future__ import annotations

import json
import unittest

from fastapi.testclient import TestClient

from reeves_api.app import create_app
from reeves_api.provider import load_provider


class ReevesAPITests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(
            create_app(allowed_origins=["https://kastorrivz-droid.github.io"]),
            raise_server_exceptions=False,
        )

    def tearDown(self) -> None:
        self.client.close()

    def test_health_and_readiness_are_non_secret(self) -> None:
        health = self.client.get("/healthz")
        ready = self.client.get("/readyz")
        self.assertEqual(health.json(), {"status": "ok", "service": "reeves-api"})
        self.assertEqual(ready.json()["provider"], "mock")
        self.assertEqual(ready.json()["validation_state"], "PROPOSED")
        self.assertEqual(ready.headers["cache-control"], "no-store")
        self.assertEqual(ready.headers["x-content-type-options"], "nosniff")

    def test_chat_contract_separates_reeves_and_argos(self) -> None:
        response = self.client.post(
            "/v1/chat",
            json={
                "message": "Кто такой Ривз?",
                "language": "ru",
                "history": [{"role": "user", "content": "Расскажи о ROZUM"}],
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["role"], "reeves")
        self.assertEqual(payload["guard"]["role"], "argos")
        self.assertEqual(payload["guard"]["status"], "PASS")
        self.assertEqual(payload["provider"], "mock")
        self.assertEqual(payload["validation_state"], "PROPOSED")
        self.assertFalse(payload["memory_persisted"])
        self.assertEqual(payload["citations"][0]["title"], "06_REEVES.md")
        self.assertNotIn("Расскажи о ROZUM", response.text)

    def test_language_is_detected_without_account_state(self) -> None:
        response = self.client.post(
            "/v1/chat",
            json={"message": "Що робить Argos?", "language": "auto"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["language"], "uk")
        self.assertEqual(response.json()["citations"][0]["status"], "VALIDATED")

    def test_unknown_fields_and_oversized_messages_are_rejected(self) -> None:
        extra = self.client.post(
            "/v1/chat",
            json={"message": "Привіт", "secret": "must not be accepted"},
        )
        too_long = self.client.post(
            "/v1/chat",
            json={"message": "x" * 4_001},
        )
        self.assertEqual(extra.status_code, 422)
        self.assertEqual(too_long.status_code, 422)

    def test_ambiguous_and_nonstandard_json_are_rejected(self) -> None:
        duplicate = self.client.post(
            "/v1/chat",
            content=b'{"message":"first","message":"second"}',
            headers={"Content-Type": "application/json"},
        )
        non_finite = self.client.post(
            "/v1/chat",
            content=b'{"message":"hello","temperature":NaN}',
            headers={"Content-Type": "application/json"},
        )
        invalid_utf8 = self.client.post(
            "/v1/chat",
            content=b'{"message":"\xff"}',
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(non_finite.status_code, 400)
        self.assertEqual(invalid_utf8.status_code, 400)
        self.assertEqual(duplicate.json()["error"]["code"], "MALFORMED_JSON")

    def test_actual_body_limit_and_content_encoding_are_enforced(self) -> None:
        with TestClient(
            create_app(allowed_origins=["https://example.com"], max_body_bytes=128),
            raise_server_exceptions=False,
        ) as client:
            oversized = client.post(
                "/v1/chat",
                content=json.dumps({"message": "x" * 200}),
                headers={"Content-Type": "application/json"},
            )
            compressed = client.post(
                "/v1/chat",
                content=b"{}",
                headers={"Content-Type": "application/json", "Content-Encoding": "gzip"},
            )
        self.assertEqual(oversized.status_code, 413)
        self.assertEqual(oversized.json()["error"]["code"], "PAYLOAD_TOO_LARGE")
        self.assertEqual(compressed.status_code, 415)

    def test_cors_is_restricted_to_configured_site(self) -> None:
        allowed = self.client.options(
            "/v1/chat",
            headers={
                "Origin": "https://kastorrivz-droid.github.io",
                "Access-Control-Request-Method": "POST",
            },
        )
        denied = self.client.options(
            "/v1/chat",
            headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"},
        )
        self.assertEqual(allowed.headers.get("access-control-allow-origin"), "https://kastorrivz-droid.github.io")
        self.assertIsNone(denied.headers.get("access-control-allow-origin"))

    def test_rate_limit_fails_closed(self) -> None:
        with TestClient(
            create_app(
                allowed_origins=["https://example.com"],
                rate_limit=1,
                rate_window_seconds=60,
            ),
            raise_server_exceptions=False,
        ) as client:
            first = client.post("/v1/chat", json={"message": "Привіт"})
            second = client.post("/v1/chat", json={"message": "Ще раз"})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)
        self.assertEqual(second.headers["retry-after"], "60")

    def test_unknown_provider_is_not_silently_accepted(self) -> None:
        with self.assertRaises(RuntimeError):
            load_provider("paid-provider-without-adapter")


if __name__ == "__main__":
    unittest.main()
