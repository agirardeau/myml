# Myml Conformance Corpus

This directory contains the canonical conformance corpus for Myml.

## Purpose

The corpus provides stable fixtures for parser and emitter validation. Each case
pairs a Myml input document with machine-readable expectations and metadata that
links the case back to the language specification.

## File Extension Convention

Myml source files in this repository use the `.yaml` extension.

This is a practical tooling convention rather than part of the Myml language
definition. A dedicated `.myml` extension may become preferable later, but
`.yaml` is the recommended extension until editor and tool support for a Myml-
specific extension is practical.

## Layout

```text
corpus/
  README.md
  status.md
  cases/
    valid/
      <case-id>/
        input.yaml
        expected_parse.json
        expected_emit_<profile>.yaml
        meta.json
    invalid/
      <case-id>/
        input.yaml
        error.json
        meta.json
```

## Case Conventions

Case identifiers use kebab-case and remain stable once published. The case id is
inferred from the directory name and is not duplicated inside `meta.json`.

### Valid cases

A valid case contains:

* `input.yaml`: Myml source text that should parse successfully
* `expected_parse.json`: canonical parsed value in a neutral data format
* one or more `expected_emit_<profile>.yaml` files: canonical emitted Myml text
  for supported emit profiles
* `meta.json`: authoritative case metadata

### Invalid cases

An invalid case contains:

* `input.yaml`: Myml source text that should be rejected
* `error.json`: structured error expectation
* `meta.json`: authoritative case metadata

`error.json` is intentionally structured around portable fields such as error
code, category, and optional location metadata. Exact human-readable message
text is not required.

## Why JSON for Control Files

JSON keeps the parse and error oracle separate from the syntax under test.

* `input.yaml` and `expected_emit_<profile>.yaml` are Myml text fixtures
* `meta.json`, `expected_parse.json`, and `error.json` are neutral test-control files

This avoids requiring a second YAML-capable parser for corpus control data and
reduces the risk that a buggy Myml implementation could accidentally agree with
its own fixtures for the wrong reasons.

## Metadata Convention

Each `meta.json` file follows this schema-by-convention:

* `summary`: short one-line description
* `tags`: topical labels
* `spec_refs`: language-spec sections or rule labels covered by the case
* `modes`: applicable parse modes such as `default`, `strict`, or `y11safety`
* `notes`: optional explanatory notes
* `emit_profiles`: mapping from emit profile names to fixture file names such as
  `expected_emit_default.yaml`
* `roundtrip_edits`: optional roundtrip edit checks keyed to emit profiles

Per-case `meta.json` files are the source of truth for case metadata. Tooling
that needs a catalog or coverage view is expected to derive it from those files.

## Parse and Emit Expectations

`expected_parse.json` stores the canonical parsed value.

`meta.json` maps each supported emit profile to a YAML fixture file containing
the canonical emitted Myml text. The current convention uses profile names such
as:

* `default`: emit behavior for plain values in default mode
* `strict`: emit behavior for plain values in strict mode
* `y11safety`: emit behavior for plain values in y11safety mode
* `roundtrip`: no-op roundtrip dump output
* additional profile names referenced by `meta.json` roundtrip edit checks

Each mapped fixture file is named `expected_emit_<profile>.yaml`.

This keeps emitter verification separate from parse verification while still
keeping profile discovery machine-readable in JSON control data and the emitted
text itself in human-readable Myml fixtures.

## Coverage Status

`status.md` records repo-level coverage notes such as covered areas, known gaps,
and follow-up work. It does not duplicate per-case metadata.

## Authoring Guidance

When adding a new case:

1. Create a new stable case directory under `cases/valid` or `cases/invalid`.
2. Keep the input focused on one primary rule or a small related cluster.
3. Add precise `spec_refs` to the case `meta.json`.
4. Prefer structured error expectations over implementation-specific wording.
5. Use JSON for metadata plus parse/error expectations, and YAML for the Myml
   input under test and each emitted-output fixture.
6. Update `status.md` only if the overall coverage picture changes.
