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

    def test_edited_document_reemits_block_scalars_with_their_values(self) -> None:
        text = "folded: >\n  one\n  two\n\n  three\n    kept\n  four\nliteral: |\n  a\n\n  b\nother: x\n"
        document = loads(text, roundtrip=True)
        document["other"] = "y"
        emitted = dumps(document, roundtrip=True)

        self.assertEqual(
            emitted,
            "folded: >\n  one two\n\n  three\n    kept\n  four\nliteral: |\n  a\n\n  b\nother: y\n",
        )
        self.assertEqual(loads(emitted), {**loads(text), "other": "y"})

    def test_values_a_block_scalar_cannot_represent_are_quoted(self) -> None:
        document = loads("text: |\n  a\n", roundtrip=True)
        document["text"] = "trailing\n\n"

        self.assertEqual(dumps(document, roundtrip=True), 'text: "trailing\\n\\n"\n')

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

    def test_nested_entry_comments_align_with_their_entries(self) -> None:
        document = as_format_aware(
            {
                "sites": sequence([entry("a.com", before="first"), entry("b.com", before="second")]),
                "settings": {"mode": entry(1, before="mode")},
                "items": [{"name": entry(2, before="name")}],
            }
        )

        text = dumps(document, roundtrip=True)

        self.assertEqual(
            text,
            "sites:\n"
            "  # first\n"
            "  - a.com\n"
            "  # second\n"
            "  - b.com\n"
            "settings:\n"
            "  # mode\n"
            "  mode: 1\n"
            "items:\n"
            "  # name\n"
            "  - name: 2\n",
        )
        self.assertEqual(loads(text), {"sites": ["a.com", "b.com"], "settings": {"mode": 1}, "items": [{"name": 2}]})

    def test_nested_flow_containers_keep_flow_style_after_edits(self) -> None:
        document = loads("plan: {dispatches: [], tags: [[a], {b: 1}]} # note\n", roundtrip=True)

        document["plan"]["dispatches"].append("x")

        self.assertEqual(dumps(document, roundtrip=True), "plan: {dispatches: [x], tags: [[a], {b: 1}]} # note\n")

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
