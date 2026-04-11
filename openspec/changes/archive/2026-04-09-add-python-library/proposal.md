# Proposal: Add Python Library

## Why

Myml now has a sufficiently detailed language definition in
`docs/lang.md`, but the repository does not yet define a reference Python
library for reading and writing Myml documents. Establishing that library now
creates a concrete implementation target for the language, gives users a
familiar Python API, and makes it possible to validate both value-oriented and
format-preserving behavior against the corpus.

## What Changes

- Add a Python `myml` library with `load`, `loads`, `dump`, and `dumps`
  functions modeled after the ergonomics of `PyYAML` and `ruamel.yaml`.
- Place the Python library in `libs/py-myml` so the repository can grow into a
  multi-language layout with sibling libraries under `libs/`.
- Keep the baseline Python library installable with no required runtime
  dependencies, while leaving room for optional extras such as performance
  accelerators in the future.
- Define default parse and emit behavior for Myml documents according to
  `docs/lang.md`, including useful errors for unsupported YAML features and
  invalid scalar forms.
- Add an optional roundtrip-preservation mode that can retain comments,
  whitespace, scalar style, key order, and other formatting details when the
  caller requests it.
- Define mode selection for default, strict, and `y11safety` behavior so
  callers can opt into stricter string rules and YAML 1.1 ambiguity safeguards.
- Extend the conformance corpus expectations so one valid case can describe
  multiple expected emitted outputs for different library settings, allowing the
  Python library to use the corpus as its primary verification source.
- Document the dependency and packaging impact of introducing a Python library
  into a repository that currently only contains the language definition and
  conformance corpus.
- Remove `prompts/python.md` from the repo so it no longer acts as an implicit
  source of requirements outside the spec-driven workflow.

## Capabilities

### New Capabilities
- `python-library`: A Python package that parses and emits Myml through a
  familiar YAML-style API, including optional roundtrip preservation and mode
  selection.

### Modified Capabilities

- `conformance-corpus`: Extend emit-expectation modeling so corpus cases can act
  as the primary verification source for mode-sensitive and roundtrip emission
  behavior.

## Impact

- Adds a new Python package surface for `myml`.
- Establishes `libs/py-myml` as the home for the Python implementation.
- Introduces Python packaging, dependency, and test-runner decisions for the
  repository.
- Requires the default runtime path to remain dependency-light and easy to
  install.
- Requires parser and emitter behavior to align with `docs/lang.md` and the
  conformance corpus.
- Expands the conformance corpus contract to cover multiple emit expectations
  for a single valid input.
- Establishes a public API contract that future implementations and integrations
  can depend on.
