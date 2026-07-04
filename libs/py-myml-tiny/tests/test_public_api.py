from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "libs" / "py-myml-tiny" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import myml_tiny  # noqa: E402
from myml_tiny import ModeError, load, loads  # noqa: E402


class PublicApiTests(unittest.TestCase):
    def test_load_reads_text_stream(self) -> None:
        self.assertEqual(load(io.StringIO("items: [1, true, null]\n")), {"items": [1, True, None]})

    def test_read_api_accepts_roundtrip_keyword_for_py_myml_compatibility(self) -> None:
        self.assertEqual(loads("ok: true\n", roundtrip=False), {"ok": True})
        self.assertEqual(load(io.StringIO("ok: true\n"), roundtrip=False), {"ok": True})

    def test_invalid_mode_raises_mode_error(self) -> None:
        with self.assertRaises(ModeError):
            loads("ok: true\n", mode="roundtrip")

    def test_emitter_api_is_not_exposed(self) -> None:
        self.assertFalse(hasattr(myml_tiny, "dump"))
        self.assertFalse(hasattr(myml_tiny, "dumps"))
        self.assertNotIn("VALID_MODES", myml_tiny.__all__)


if __name__ == "__main__":
    unittest.main()
