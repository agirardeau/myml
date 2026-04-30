# `myml` Python Library

This package provides the reference Python implementation for Myml.

## Public API

The top-level API exposes:

* `load(stream, *, mode="standard", roundtrip=False)`
* `loads(text, *, mode="standard", roundtrip=False)`
* `dump(value, stream, *, mode="standard", roundtrip=False)`
* `dumps(value, *, mode="standard", roundtrip=False)`
* `scalar(value, *, style="plain")`
* `mapping(value=None, *, style="block")`
* `sequence(value=None, *, style="block")`
* `entry(value, *, before=None, eol_comment=None)`
* `as_format_aware(value, *, mode="standard")`

The supported modes are:

* `standard`
* `strict`

The library has no required runtime dependencies. The language definition in
`/home/andrew/truehome/repos/myml/wt1/docs/lang.md` and the OpenSpec artifacts
under `/home/andrew/truehome/repos/myml/wt1/openspec/` are the source of truth
for behavior.

## Development

Build distribution artifacts with `uv`:

```bash
uv build
```

Run the test suite against an editable checkout:

```bash
uv run --with-editable . python -m unittest discover tests
```

## Format-Aware Editing

`roundtrip=True` remains the way to load a document with formatting metadata
attached. The returned mapping and sequence wrappers now expose a format-aware
editing API that preserves parsed comments, styles, and key order while also
letting callers inject new formatting metadata deliberately.

Use `scalar()`, `mapping()`, and `sequence()` for node-local formatting:

```python
from myml import dumps, loads, scalar

document = loads("title: hello\n", roundtrip=True)
document["title"] = scalar("hello", style="single")

assert dumps(document, roundtrip=True) == "title: 'hello'\n"
```

Use `entry()` for entry-local formatting such as pre-node comments and
end-of-line comments:

```python
from myml import dumps, entry, loads, scalar

document = loads("title: hello\n", roundtrip=True)
document["body"] = entry(
    scalar("line 1\nline 2\n", style="literal"),
    before="body comment",
    eol_comment="body tail",
)

assert dumps(document, roundtrip=True) == (
    "title: hello\n"
    "# body comment\n"
    "body: | # body tail\n"
    "  line 1\n"
    "  line 2\n"
)
```

Use `as_format_aware()` when you want the same wrapper model without reparsing
text:

```python
from myml import as_format_aware, dumps

document = as_format_aware({"a": 1, "b": 2})
document.insert("c", 3, before="b")
document.move_after("a", "b")

assert dumps(document, roundtrip=True) == "c: 3\nb: 2\na: 1\n"
```

Format-aware mappings expose `entry(key)`, `insert()`, `move_before()`,
`move_after()`, and `reorder()`. Format-aware sequences expose `entry(index)`.
Ordinary indexed reads still return plain Python scalars so existing
roundtrip-oriented code keeps its current read behavior.
