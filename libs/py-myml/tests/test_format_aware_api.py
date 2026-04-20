from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "libs" / "py-myml" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from myml import as_format_aware, dumps, entry, loads, mapping, scalar, sequence  # noqa: E402


class FormatAwareApiTests(unittest.TestCase):
    maxDiff = None

    def test_mapping_entry_accessor_preserves_scalar_reads(self) -> None:
        document = loads("name: hello # note\n", roundtrip=True)

        self.assertEqual(document["name"], "hello")

        slot = document.entry("name")
        self.assertEqual(slot.eol_comment, "# note")
        slot.eol_comment = "updated"

        self.assertEqual(dumps(document, roundtrip=True), "name: hello # updated\n")

    def test_sequence_entry_accessor_updates_item_comments(self) -> None:
        document = loads("- alpha # first\n", roundtrip=True)

        self.assertEqual(document[0], "alpha")

        slot = document.entry(0)
        slot.before = "inserted"
        slot.eol_comment = "# changed"

        self.assertEqual(dumps(document, roundtrip=True), "# inserted\n- alpha # changed\n")

    def test_constructors_and_mapping_placement_are_emitted(self) -> None:
        document = as_format_aware({"title": "draft", "tail": True})
        document["title"] = scalar("hello", style="single")
        document.insert(
            "body",
            entry(
                scalar("line 1\nline 2\n", style="literal"),
                before="body comment",
                eol_comment="body tail",
            ),
            after="title",
        )
        document.insert("tags", sequence([scalar("x", style="double")], style="flow"), before="tail")
        document.move_before("tail", "body")

        self.assertEqual(
            dumps(document, roundtrip=True),
            "title: 'hello'\n"
            "tail: true\n"
            "# body comment\n"
            "body: | # body tail\n"
            "  line 1\n"
            "  line 2\n"
            "tags: [\"x\"]\n",
        )

    def test_mapping_reorder_requires_complete_key_set(self) -> None:
        document = as_format_aware({"a": 1, "b": 2, "c": 3})

        with self.assertRaises(ValueError):
            document.reorder(["b", "a"])

        document.reorder(["c", "a", "b"])
        self.assertEqual(dumps(document, roundtrip=True), "c: 3\na: 1\nb: 2\n")

    def test_insert_rejects_ambiguous_anchor_request(self) -> None:
        document = as_format_aware({"a": 1})

        with self.assertRaises(ValueError):
            document.insert("b", 2, before="a", after="a")

    def test_as_format_aware_rejects_scalars(self) -> None:
        with self.assertRaises(TypeError):
            as_format_aware("value")

    def test_nested_container_constructors_preserve_requested_styles(self) -> None:
        document = as_format_aware(
            mapping(
                {
                    "flow_map": mapping({"inner": scalar("quoted", style="double")}, style="flow"),
                    "flow_seq": sequence([scalar("quoted", style="single")], style="flow"),
                }
            )
        )

        self.assertEqual(
            dumps(document, roundtrip=True),
            'flow_map: {inner: "quoted"}\n'
            "flow_seq: ['quoted']\n",
        )


if __name__ == "__main__":
    unittest.main()
