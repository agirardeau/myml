# Minimal Yaml - The Yaml Subset That Doesn't Suck

The language definition lives in [`docs/lang.md`](docs/lang.md), and the
specifications live under [`docs/specs/`](docs/specs/).

The reference Python implementation lives in [`libs/py-myml`](libs/py-myml)
and is verified against the checked-in corpus in [`corpus/`](corpus/).

Standard mode treats YAML 1.1-ambiguous plain scalars such as `yes`, `no`,
`on`, `off`, `y`, `n`, ISO-like date/time values, `0123`, and sexagesimal-like
values such as `13:22` as strings unless they match a supported Myml scalar
form.

## Development

Requires `just`.

```bash
# Test
just test-py-myml
just test-py-myml-tiny
just test-serde-myml

# Release
just release-python py-myml major|minor|patch
just release-python py-myml-tiny major|minor|patch
just release-rust major|minor|patch
```

Release commands require a clean working tree. They verify the library, create a release commit, and an annotated version tag; push the commit and the tag named in the script's output afterward.
