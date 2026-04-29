## Why

The corpus emit-profile contract currently leaves room for arbitrary emit
`options`, but the checked-in harness only has one supported optional feature:
`roundtrip`. A one-off `roundtrip_edit_note` case stretches the corpus from
baseline and roundtrip emission into scripted mutation behavior, which makes
the emit-test contract less clear than the implementation it is meant to
verify.

## What Changes

- Define that corpus emit profiles only support baseline mode-based emission
  and the optional `roundtrip` feature beyond that baseline.
- Remove corpus guidance that implies arbitrary emit-profile `options` are part
  of the supported checked-in contract.
- Remove the `roundtrip_edit_note` emit profile and its fixture from the corpus
  so corpus-backed emit verification stays focused on baseline emission and
  roundtrip-preserving re-emission.
- Tighten the Python corpus harness to reject unsupported emit-test options
  instead of silently allowing new option shapes.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `conformance-corpus`: restrict emit-profile options to the supported
  roundtrip-only contract for corpus-driven emit verification.

## Impact

- `corpus/README.md` and corpus case metadata conventions
- corpus fixtures under `corpus/cases/comments-and-empty-lines/`
- `libs/py-myml/tests/test_corpus.py`
