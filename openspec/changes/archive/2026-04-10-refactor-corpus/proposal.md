## Why

The current corpus format splits cases into `valid/` and `invalid/`
directories and treats parse success, parse failure, and emitted output as
different kinds of cases. That structure worked for the initial corpus, but it
does not model mode-specific behavior cleanly now that one input may succeed in
some modes, fail in others, and produce multiple emitted outputs under
different serializer settings.

The corpus needs a single per-input structure that can express parse outcomes
for all supported modes, keep one canonical semantic graph for successful
parses, and define multiple emit expectations without forcing ad hoc sidecar
files or duplicated cases.

## What Changes

- Refactor the corpus directory layout so every case lives directly under
  `corpus/cases/<case-id>/` rather than under `valid/` and `invalid/`
  subdirectories.
- Replace the current `modes`, `emit_profiles`, and `roundtrip_edits`
  conventions in `meta.json` with explicit `parse_profiles` and `emit_profiles`
  maps keyed by profile id.
- Rename `expected_parse.json` to `expected_node_graph.json` and make it the
  canonical semantic graph artifact shared by successful parse profiles for a
  case.
- Allow parse and emit failures to be declared inline in `meta.json` using
  `expect_error` rather than separate `error.json` files.
- Allow parse profiles to target multiple modes through a required `modes`
  field, with support for the special value `"all"`.
- Add capability gating through an optional `requires` array on parse and emit
  profiles.
- Require each case to include at least one parse profile and at least one emit
  profile with no `requires`, so there is always a baseline parse and emit
  expectation that applies without optional features.
- Update contributor documentation and downstream harness expectations to match
  the refactored corpus model.

## Capabilities

### New Capabilities

### Modified Capabilities

- `conformance-corpus`: Change the corpus layout and metadata schema so one
  case can represent multiple parse-mode outcomes and multiple emit
  expectations while keeping one canonical semantic graph.

## Impact

- Changes the on-disk contract for files under `corpus/cases/`.
- Changes the schema-by-convention for per-case `meta.json`.
- Replaces `error.json` and `expected_parse.json` conventions with inline error
  expectations and `expected_node_graph.json`.
- Requires updates to corpus documentation and any harnesses or tools that read
  corpus cases, including the Python verification harness.
