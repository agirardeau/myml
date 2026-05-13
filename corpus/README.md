# Myml Conformance Corpus

This directory contains the canonical conformance corpus for Myml.

## Purpose

The corpus provides stable fixtures for parser and emitter validation. Each case
pairs one Myml input document with machine-readable expectations and metadata
that links the case back to the language specification.

## File Extension Convention

Myml source files in this repository use the `.yaml` extension.

This is a practical tooling convention rather than part of the Myml language
definition. A dedicated `.myml` extension may become preferable later, but
`.yaml` remains the recommended extension until editor and tool support for a
Myml-specific extension is practical.

## Layout

```text
corpus/
  README.md
  status.md
  cases/
    <case-id>/
      input.yaml
      expected_node_graph.json          # present when one or more parse profiles succeed
      expected_emit_<profile>.yaml      # present for successful emit profiles
      meta.json
```

Every case lives directly under `corpus/cases/<case-id>/`. There is no separate
`valid/` or `invalid/` directory split. A case directory is the stable identity
for one input document, and `meta.json` describes how that same input behaves in
standard mode, strict mode, and each supported emit configuration.

Case identifiers use kebab-case and remain stable once published. The case id is
inferred from the directory name and is not duplicated inside `meta.json`.

## Why JSON for Control Files

JSON keeps the semantic oracle and structured error expectations separate from
the Myml syntax under test.

* `input.yaml` and `expected_emit_<profile>.yaml` are Myml text fixtures
* `meta.json` and `expected_node_graph.json` are neutral test-control files
* parse and emit failures are represented as structured JSON data inline in
  `meta.json`

This avoids requiring a second YAML-capable parser for corpus control data and
reduces the risk that a buggy Myml implementation could accidentally agree with
its own fixtures for the wrong reasons.

## Metadata Convention

Each `meta.json` file follows this schema-by-convention:

* `summary`: short one-line description
* `tags`: topical labels
* `spec_refs`: language-spec sections or rule labels covered by the case
* `notes`: optional explanatory notes
* `parse_profiles`: mapping from parse profile ids to parse expectations
* `emit_profiles`: mapping from emit profile ids to emit expectations

Per-case `meta.json` files are the source of truth for case metadata. Tooling
that needs a catalog or coverage view is expected to derive it from those files.

### Parse Profiles

Each entry in `parse_profiles` is keyed by a contributor-chosen profile id and
declares:

* `modes`: either an explicit array of supported parse modes or the scalar
  string `"all"`
* optional `requires`: optional implementation capabilities needed for the
  profile to be relevant
* exactly one of:
  * `expect_node_graph`: references `expected_node_graph.json`
  * `expect_error`: structured inline parse failure expectation

`expect_error` is intentionally structured around portable fields such as error
code, category, and optional location metadata. Exact human-readable message
text is not required.

### Emit Profiles

Each entry in `emit_profiles` is keyed by a contributor-chosen profile id and
declares:

* `mode`: the emitter mode to use
* optional `options`: supported only for roundtrip emit profiles
* optional `requires`: optional implementation capabilities needed for the
  profile to be relevant
* exactly one of:
  * `expect_output`: references an `expected_emit_<profile>.yaml` fixture
  * `expect_error`: structured inline emit failure expectation

Emit profiles without `options` are baseline profiles for their declared mode.
The only supported non-baseline emit option is `options.roundtrip: true`, which
marks a profile that must parse with `roundtrip=True` before re-emission. A
roundtrip emit profile also declares `requires: ["roundtrip"]`.

No other emit option keys or values are part of the checked-in corpus
contract. If a future corpus need goes beyond baseline mode-based emission and
roundtrip preservation, it should be introduced with an explicit spec change
rather than ad hoc metadata.

## Profile Invariants

Parse profiles must cover every supported parse mode exactly once.

* If a profile uses `modes: "all"`, it is the only parse profile for that case.
* Otherwise, the explicit `modes` arrays across all parse profiles form an exact
  partition of the supported parse modes.
* Every case includes at least one parse profile with no `requires`.

Successful parse profiles within a case all share one canonical
`expected_node_graph.json` fixture. That artifact captures the semantic node
graph for the case independent of parser mode.

Cases with at least one successful parse profile also include at least one emit
profile with no `requires`, so baseline implementations still have an
unconditional emit expectation to exercise.

## Parse and Emit Expectations

`expected_node_graph.json` stores the canonical parsed value for any successful
parse profile in the case.

Emit fixtures remain separate YAML files named `expected_emit_<profile>.yaml`.
This keeps emitter verification separate from parse verification while still
keeping profile discovery machine-readable in JSON control data and the emitted
text itself in human-readable Myml fixtures.

## Coverage Status

`status.md` records repo-level coverage notes such as covered areas, known gaps,
and follow-up work. It does not duplicate per-case metadata.

## Authoring Guidance

When adding a new case:

1. Create a new stable case directory under `cases/<case-id>/`.
2. Keep the input focused on one primary rule or a small related cluster.
3. For invalid inputs, prefer one invalid form per case so the expected error
   proves that exact form. Parsers usually report the first error they find, so
   combining multiple invalid forms can leave later forms unexercised.
4. Use a shared case-id prefix for related invalid lexical boundary cases, such
   as `unquoted-scalar-invalid-<form>` for invalid unquoted-scalar characters.
5. Add precise `spec_refs` to the case `meta.json`.
6. Use `parse_profiles` to describe how the same input behaves across supported
   parse modes.
7. Reuse one canonical `expected_node_graph.json` for all successful parse
   profiles in the case.
8. Keep structured parse and emit failure expectations inline in `meta.json`.
9. Use `requires` only for optional capabilities, and ensure a baseline parse
   profile and baseline emit profile remain available without `requires` when
   the case has a successful parse path.
10. Update `status.md` only if the overall coverage picture changes.
