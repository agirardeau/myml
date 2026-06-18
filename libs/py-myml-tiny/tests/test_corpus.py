from __future__ import annotations

import json
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "libs" / "py-myml-tiny" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from myml_tiny import ParseError, loads  # noqa: E402

SUPPORTED_PARSE_MODES = ("standard", "strict")
SUPPORTED_OPTIONAL_FEATURES: set[str] = set()


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


def expand_modes(mode_spec):
    if mode_spec == "all":
        return list(SUPPORTED_PARSE_MODES)
    return list(mode_spec)


def profile_supported(profile):
    required = set(profile.get("requires", []))
    return required.issubset(SUPPORTED_OPTIONAL_FEATURES)


class CorpusTests(unittest.TestCase):
    maxDiff = None

    def test_cases_parse_against_corpus(self):
        cases_root = ROOT / "corpus" / "cases"
        for case_dir in sorted(cases_root.iterdir()):
            with self.subTest(case=case_dir.name):
                meta = json.loads((case_dir / "meta.json").read_text())
                source = (case_dir / "input.yaml").read_text()

                for profile_id, profile in meta["parse_profiles"].items():
                    if not profile_supported(profile):
                        continue
                    for mode in expand_modes(profile["modes"]):
                        with self.subTest(case=case_dir.name, parse_profile=profile_id, mode=mode):
                            if "expect_node_graph" in profile:
                                expected = json.loads((case_dir / profile["expect_node_graph"]).read_text())
                                self.assertEqual(normalize(loads(source, mode=mode)), expected)
                            else:
                                expected_error = profile["expect_error"]
                                with self.assertRaises(ParseError) as raised:
                                    loads(source, mode=mode)
                                error = raised.exception
                                self.assertEqual(error.code, expected_error["code"])
                                self.assertEqual(error.category, expected_error["category"])
                                self.assertEqual(error.line, expected_error["line"])
                                self.assertEqual(error.column, expected_error["column"])


if __name__ == "__main__":
    unittest.main()
