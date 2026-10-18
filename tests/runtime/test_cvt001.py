from __future__ import annotations

import hashlib
import json
import unittest
from importlib import resources

from rozum.canonical import build_signing_input
from rozum.conformance import run_cvt001
from rozum.crypto import sign_ed25519

from .common import BUNDLE, load_json


class CVT001Tests(unittest.TestCase):
    def test_packaged_schema_matches_canonical_schema(self) -> None:
        canonical = json.loads(
            (BUNDLE.parents[2] / "schemas/ROZUM_AI_v2.1.schema.json").read_text(
                encoding="utf-8"
            )
        )
        packaged = json.loads(
            resources.files("rozum")
            .joinpath("resources/ROZUM_AI_v2.1.schema.json")
            .read_text(encoding="utf-8")
        )
        self.assertEqual(packaged, canonical)

    def test_runtime_harness_reproduces_all_six_assertions(self) -> None:
        result = run_cvt001(BUNDLE)
        self.assertEqual(result["overall_status"], "PASS")
        self.assertEqual(len(result["assertions"]), 6)
        self.assertTrue(all(item["status"] == "PASS" for item in result["assertions"]))

    def test_exact_canonical_bytes_and_digest(self) -> None:
        envelope = load_json("envelope.unsigned.json")
        actual = build_signing_input(envelope)
        self.assertEqual(actual, (BUNDLE / "signing_input.bin").read_bytes())
        self.assertEqual(
            hashlib.sha256(actual).hexdigest(),
            (BUNDLE / "signing_input.sha256").read_text(encoding="ascii"),
        )

    def test_deterministic_test_signature(self) -> None:
        seed = bytes.fromhex(
            "9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60"
        )
        envelope = load_json("envelope.unsigned.json")
        expected = (BUNDLE / "signature.b64").read_text(encoding="ascii")
        self.assertEqual(sign_ed25519(envelope, seed), expected)


if __name__ == "__main__":
    unittest.main()
