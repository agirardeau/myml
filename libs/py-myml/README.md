# `myml` Python Library

This package provides the reference Python implementation for Myml.

## Public API

The top-level API exposes:

* `load(stream, *, mode="default", roundtrip=False)`
* `loads(text, *, mode="default", roundtrip=False)`
* `dump(value, stream, *, mode="default", roundtrip=False)`
* `dumps(value, *, mode="default", roundtrip=False)`

The supported modes are:

* `default`
* `strict`
* `y11safety`

The library has no required runtime dependencies. The language definition in
`/home/andrew/truehome/repos/myml/wt1/docs/lang.md` and the OpenSpec artifacts
under `/home/andrew/truehome/repos/myml/wt1/openspec/` are the source of truth
for behavior.
