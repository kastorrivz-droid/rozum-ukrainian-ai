from __future__ import annotations

import json
import shutil
import subprocess
import unittest

from rozum.canonical import canonicalize_json

from .common import ROOT


VECTORS = ROOT / "tests/interoperability/CVT-002/jcs_vectors.json"
NODE_VERIFIER = ROOT / "runtime/js-jcs/verify-cvt001.mjs"


class CrossRuntimeJCSTests(unittest.TestCase):
    def test_python_matches_all_shared_jcs_vectors(self) -> None:
        suite = json.loads(VECTORS.read_text(encoding="utf-8"))
        for vector in suite["vectors"]:
            with self.subTest(vector=vector["name"]):
                self.assertEqual(
                    canonicalize_json(vector["value"]).hex(),
                    vector["expected_utf8_hex"],
                )

    @unittest.skipUnless(shutil.which("node"), "Node.js is not installed")
    def test_independent_node_implementation_matches(self) -> None:
        completed = subprocess.run(
            ["node", str(NODE_VERIFIER), "--json"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(all(item["status"] == "PASS" for item in result["assertions"]))


if __name__ == "__main__":
    unittest.main()
