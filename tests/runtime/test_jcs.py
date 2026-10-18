from __future__ import annotations

import unittest

import rfc8785

from rozum.canonical import canonicalize_json


class JCSTests(unittest.TestCase):
    def test_nested_keys_unicode_and_literals_have_exact_bytes(self) -> None:
        value = {
            "z": 1,
            "é": "Привет",
            "a": {"b": 2, "a": [3, True, None]},
        }
        expected = (
            '{"a":{"a":[3,true,null],"b":2},"z":1,"é":"Привет"}'.encode("utf-8")
        )
        self.assertEqual(canonicalize_json(value), expected)

    def test_numbers_follow_jcs_serialization(self) -> None:
        value = {"negative_zero": -0.0, "one": 1.0, "small": 0.002, "large": 1e30}
        expected = b'{"large":1e+30,"negative_zero":0,"one":1,"small":0.002}'
        self.assertEqual(canonicalize_json(value), expected)

    def test_non_finite_numbers_are_rejected(self) -> None:
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                with self.assertRaises(rfc8785.CanonicalizationError):
                    canonicalize_json({"value": value})


if __name__ == "__main__":
    unittest.main()
