from __future__ import annotations

import json
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "libs" / "py-myml" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from myml import dumps, loads  # noqa: E402
from myml.errors import ParseError  # noqa: E402


def normalize(value):
    if isinstance(value, dict):
        return {key: normalize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [normalize(item) for item in value]
    if isinstance(value, float):
        if math.isnan(value):
            return ".nan"
        if math.isinf(value):
            return ".inf" if value > 0 else "-.inf"
    return value


def materialize(value):
    if isinstance(value, dict):
        return {key: materialize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [materialize(item) for item in value]
    if value == ".inf":
        return float("inf")
    if value == "-.inf":
        return float("-inf")
    if value == ".nan":
        return float("nan")
    return value


class CorpusTests(unittest.TestCase):
    maxDiff = None

    def test_valid_cases(self):
        valid_root = ROOT / "corpus" / "cases" / "valid"
        for case_dir in sorted(valid_root.iterdir()):
            with self.subTest(case=case_dir.name):
                meta = json.loads((case_dir / "meta.json").read_text())
                expected_parse = json.loads((case_dir / "expected_parse.json").read_text())
                semantic_value = materialize(expected_parse)
                emit_profiles = {
                    profile: (case_dir / filename).read_text()
                    for profile, filename in meta.get("emit_profiles", {}).items()
                }
                source = (case_dir / "input.yaml").read_text()
                for mode in meta["modes"]:
                    parsed = loads(source, mode=mode)
                    self.assertEqual(normalize(parsed), expected_parse)
                if "default" in emit_profiles:
                    self.assertEqual(dumps(semantic_value, mode="default"), emit_profiles["default"])
                if "strict" in emit_profiles:
                    self.assertEqual(dumps(semantic_value, mode="strict"), emit_profiles["strict"])
                if "y11safety" in emit_profiles:
                    self.assertEqual(dumps(semantic_value, mode="y11safety"), emit_profiles["y11safety"])
                if "roundtrip" in emit_profiles:
                    parsed = loads(source, mode="default", roundtrip=True)
                    self.assertEqual(dumps(parsed, mode="default", roundtrip=True), emit_profiles["roundtrip"])
                for edit in meta.get("roundtrip_edits", []):
                    parsed = loads(source, mode="default", roundtrip=True)
                    target = parsed
                    path = edit["path"]
                    for key in path[:-1]:
                        target = target[key]
                    target[path[-1]] = edit["value"]
                    self.assertEqual(dumps(parsed, mode="default", roundtrip=True), emit_profiles[edit["emit_profile"]])

    def test_invalid_cases(self):
        invalid_root = ROOT / "corpus" / "cases" / "invalid"
        for case_dir in sorted(invalid_root.iterdir()):
            with self.subTest(case=case_dir.name):
                meta = json.loads((case_dir / "meta.json").read_text())
                expected = json.loads((case_dir / "error.json").read_text())
                source = (case_dir / "input.yaml").read_text()
                for mode in meta["modes"]:
                    with self.assertRaises(ParseError) as raised:
                        loads(source, mode=mode)
                    error = raised.exception
                    self.assertEqual(error.code, expected["code"])
                    self.assertEqual(error.category, expected["category"])
                    self.assertEqual(error.line, expected["line"])
                    self.assertEqual(error.column, expected["column"])


if __name__ == "__main__":
    unittest.main()
