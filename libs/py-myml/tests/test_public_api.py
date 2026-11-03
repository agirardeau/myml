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
        texts = ["True", "-0", "1_000", " pad", "pad ", "~", "a #b", "x", "a\x80b", "a\ufffeb", "a\x0cb"]
        value = {"items": texts, **{text: index for index, text in enumerate(texts)}}

        self.assertEqual(loads(dumps(value)), value)


if __name__ == "__main__":
    unittest.main()
