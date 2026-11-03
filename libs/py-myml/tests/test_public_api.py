from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "libs" / "py-myml" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from myml import dumps, loads  # noqa: E402


class PublicApiTests(unittest.TestCase):
    def test_nested_sequence_mapping_round_trips(self) -> None:
        value = {
            "assertions": [
                {
                    "id": "assertions-0",
                    "verdict": "pass",
                }
            ]
        }

        self.assertEqual(loads(dumps(value)), value)

    def test_strings_that_would_not_parse_back_are_quoted(self) -> None:
        texts = ["True", "-0", "1_000", " pad", "pad ", "~", "a #b", "x", "a\x80b", "a\ufffeb", "a\x0cb", "a\u200bb\u202ec\ufeff"]
        value = {"items": texts, **{text: index for index, text in enumerate(texts)}}

        self.assertEqual(loads(dumps(value)), value)

    def test_floats_keep_their_type_and_value(self) -> None:
        self.assertIsInstance(loads("1e6"), float)
        cases = [
            (1e6, "1e6"),
            (-1e6, "-1e6"),
            (150.0, "150.0"),
            (1000.0, "1000.0"),
            (10000.0, "1e4"),
            (1.0, "1.0"),
            (0.0, "0.0"),
            (-0.0, "-0.0"),
            (0.5, "0.5"),
            (0.0001, "0.0001"),
            (0.00001, "1e-5"),
            (1.25e-7, "1.25e-7"),
            (0.1234567, "0.1234567"),
            (0.1 + 0.2, "0.30000000000000004"),
            (1e300, "1e300"),
            (sys.float_info.max, "1.7976931348623157e308"),
        ]
        for value, text in cases:
            with self.subTest(text=text):
                self.assertEqual(dumps(value), f"{text}\n")
                parsed = loads(text)
                self.assertIsInstance(parsed, float)
                self.assertEqual(repr(parsed), repr(value))
        self.assertEqual(dumps(1000000), "1000000\n")

    def test_multiline_strings_use_literal_blocks_when_representable(self) -> None:
        self.assertEqual(dumps({"items": [{"text": "line\n"}]}), "items:\n  - text: |\n      line\n")
        self.assertEqual(dumps("\na\n  \n"), "|\n\n  a\n    \n")
        for text in ["no newline\nend", "two\n\n", " lead\n", "tab\there\n", "  \nspaces before\n", "zero\u200bwidth\n", "bom\ufeff\n"]:
            with self.subTest(text=text):
                emitted = dumps({"text": text})
                self.assertTrue(emitted.startswith('text: "'), emitted)
                self.assertEqual(loads(emitted), {"text": text})


if __name__ == "__main__":
    unittest.main()
