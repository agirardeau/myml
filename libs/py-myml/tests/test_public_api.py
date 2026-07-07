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


if __name__ == "__main__":
    unittest.main()
