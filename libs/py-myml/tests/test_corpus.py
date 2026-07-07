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
from myml.errors import MymlError, ParseError  # noqa: E402
from myml.modes import VALID_MODES  # noqa: E402

SUPPORTED_PARSE_MODES = tuple(VALID_MODES)
SUPPORTED_OPTIONAL_FEATURES = {"roundtrip"}


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


def expand_modes(mode_spec):
    if mode_spec == "all":
        return list(SUPPORTED_PARSE_MODES)
    return list(mode_spec)


def profile_supported(profile):
    required = set(profile.get("requires", []))
    return required.issubset(SUPPORTED_OPTIONAL_FEATURES)


class CorpusTests(unittest.TestCase):
    maxDiff = None

    def validate_parse_profiles(self, case_dir, parse_profiles):
        self.assertTrue(parse_profiles, "Each case must define parse_profiles.")
        self.assertTrue(
            any(not profile.get("requires") for profile in parse_profiles.values()),
            "Each case must include a baseline parse profile with no requires.",
        )

        covered_modes = set()
        uses_all = False
        successful_profiles = []

        for profile_id, profile in parse_profiles.items():
            with self.subTest(case=case_dir.name, parse_profile=profile_id, invariant="shape"):
                mode_spec = profile["modes"]
                modes = expand_modes(mode_spec)
                if mode_spec == "all":
                    self.assertFalse(uses_all, "Only one parse profile may use modes='all'.")
                    uses_all = True
                    self.assertEqual(
                        len(parse_profiles),
                        1,
                        "A case using modes='all' cannot define other parse profiles.",
                    )
                else:
                    self.assertIsInstance(mode_spec, list, "Explicit modes must be listed.")
                    self.assertTrue(mode_spec, "Explicit mode lists cannot be empty.")

                expects_graph = "expect_node_graph" in profile
                expects_error = "expect_error" in profile
                self.assertNotEqual(
                    expects_graph,
                    expects_error,
                    "Each parse profile must declare exactly one expectation kind.",
                )

                for mode in modes:
                    self.assertIn(mode, SUPPORTED_PARSE_MODES)
                    self.assertNotIn(mode, covered_modes, f"Mode {mode} is covered more than once.")
                    covered_modes.add(mode)

                if expects_graph:
                    successful_profiles.append(profile)
                    self.assertEqual(
                        profile["expect_node_graph"],
                        "expected_node_graph.json",
                        "Successful parse profiles must reference the canonical node graph fixture.",
                    )

        self.assertEqual(
            covered_modes,
            set(SUPPORTED_PARSE_MODES),
            "Parse profiles must cover every supported parse mode exactly once.",
        )

        node_graph_path = case_dir / "expected_node_graph.json"
        if successful_profiles:
            self.assertTrue(node_graph_path.exists(), "Successful parse profiles require expected_node_graph.json.")
            self.assertEqual(
                len(list(case_dir.glob("expected_node_graph.json"))),
                1,
                "Each successful case must have exactly one canonical expected_node_graph.json.",
            )
        else:
            self.assertFalse(
                node_graph_path.exists(),
                "Cases without successful parse profiles should not define expected_node_graph.json.",
            )

        return successful_profiles

    def validate_emit_profiles(self, successful_profiles, emit_profiles):
        if successful_profiles:
            self.assertTrue(
                any(not profile.get("requires") for profile in emit_profiles.values()),
                "Cases with a successful parse path must include a baseline emit profile with no requires.",
            )
        for profile_id, profile in emit_profiles.items():
            with self.subTest(emit_profile=profile_id, invariant="shape"):
                options = profile.get("options")
                if options is None:
                    continue

                self.assertIsInstance(options, dict, "Emit profile options must be an object when present.")
                self.assertEqual(
                    options,
                    {"roundtrip": True},
                    "Emit profile options only support {'roundtrip': True}.",
                )
                self.assertEqual(
                    profile.get("requires"),
                    ["roundtrip"],
                    "Roundtrip emit profiles must declare requires=['roundtrip'].",
                )

    def test_cases(self):
        cases_root = ROOT / "corpus" / "cases"
        for case_dir in sorted(cases_root.iterdir()):
            with self.subTest(case=case_dir.name):
                meta = json.loads((case_dir / "meta.json").read_text())
                source = (case_dir / "input.yaml").read_text()
                parse_profiles = meta["parse_profiles"]
                emit_profiles = meta.get("emit_profiles", {})

                successful_profiles = self.validate_parse_profiles(case_dir, parse_profiles)
                self.validate_emit_profiles(successful_profiles, emit_profiles)

                expected_node_graph = None
                semantic_value = None
                if successful_profiles:
                    expected_node_graph = json.loads((case_dir / "expected_node_graph.json").read_text())
                    semantic_value = materialize(expected_node_graph)

                for profile_id, profile in parse_profiles.items():
                    if not profile_supported(profile):
                        continue
                    for mode in expand_modes(profile["modes"]):
                        with self.subTest(case=case_dir.name, parse_profile=profile_id, mode=mode):
                            if "expect_node_graph" in profile:
                                parsed = loads(source, mode=mode)
                                self.assertEqual(normalize(parsed), expected_node_graph)
                            else:
                                expected_error = profile["expect_error"]
                                with self.assertRaises(ParseError) as raised:
                                    loads(source, mode=mode)
                                error = raised.exception
                                self.assertEqual(error.code, expected_error["code"])
                                self.assertEqual(error.category, expected_error["category"])
                                self.assertEqual(error.line, expected_error["line"])
                                self.assertEqual(error.column, expected_error["column"])

                for profile_id, profile in emit_profiles.items():
                    if not profile_supported(profile):
                        continue
                    with self.subTest(case=case_dir.name, emit_profile=profile_id):
                        options = profile.get("options", {})
                        expects_output = "expect_output" in profile
                        expects_error = "expect_error" in profile
                        self.assertNotEqual(
                            expects_output,
                            expects_error,
                            "Each emit profile must declare exactly one expectation kind.",
                        )

                        if expects_output:
                            expected_output = (case_dir / profile["expect_output"]).read_text()
                            if options.get("roundtrip"):
                                roundtrip_value = loads(source, mode=profile["mode"], roundtrip=True)
                                actual_output = dumps(roundtrip_value, mode=profile["mode"], roundtrip=True)
                            else:
                                actual_output = dumps(semantic_value, mode=profile["mode"])
                            self.assertEqual(actual_output, expected_output)
                            reparsed = loads(actual_output, mode=profile["mode"])
                            self.assertEqual(normalize(reparsed), expected_node_graph)
                        else:
                            expected_error = profile["expect_error"]
                            with self.assertRaises(MymlError) as raised:
                                if options.get("roundtrip"):
                                    roundtrip_value = loads(source, mode=profile["mode"], roundtrip=True)
                                    dumps(roundtrip_value, mode=profile["mode"], roundtrip=True)
                                else:
                                    dumps(semantic_value, mode=profile["mode"])
                            error = raised.exception
                            self.assertEqual(error.code, expected_error["code"])
                            self.assertEqual(error.category, expected_error["category"])
                            self.assertEqual(error.line, expected_error["line"])
                            self.assertEqual(error.column, expected_error["column"])


if __name__ == "__main__":
    unittest.main()
