# Tasks: Refactor Corpus

## 1. Corpus schema and documentation

- [x] 1.1 Update `corpus/README.md` to document the flat `corpus/cases/<case-id>/` layout and remove the `valid/` and `invalid/` directory split
- [x] 1.2 Document the new `meta.json` schema-by-convention, including `parse_profiles`, `emit_profiles`, `modes`, `mode`, `options`, `requires`, `expect_node_graph`, `expect_output`, and `expect_error`
- [x] 1.3 Document the profile invariants: parse profiles cover every supported parse mode exactly once, `"all"` is a scalar shorthand for all supported parse modes, and each case includes baseline parse and emit profiles with no `requires`

## 2. Corpus fixture migration

- [x] 2.1 Move existing case directories from `corpus/cases/valid/` and `corpus/cases/invalid/` into the new flat `corpus/cases/<case-id>/` layout
- [x] 2.2 Rename each `expected_parse.json` fixture to `expected_node_graph.json` and update metadata references accordingly
- [x] 2.3 Fold each existing `error.json` expectation into the relevant parse profile as inline `expect_error` data and remove the obsolete sidecar files
- [x] 2.4 Convert existing per-case metadata from `modes`, legacy `emit_profiles`, and `roundtrip_edits` into explicit `parse_profiles` and `emit_profiles`

## 3. Harness and tooling updates

- [x] 3.1 Update the Python corpus harness to read the flat case layout and consume `parse_profiles` plus `emit_profiles` from `meta.json`
- [x] 3.2 Teach the harness to enforce parse-profile coverage rules, including explicit mode partitions and the scalar `"all"` shorthand
- [x] 3.3 Teach the harness to honor `requires`, skip unsupported optional profiles, and use `options.roundtrip` to decide when an emit profile requires roundtrip-preserving parsing

## 4. Verification

- [x] 4.1 Verify that every migrated case has exactly one canonical `expected_node_graph.json` for successful parse profiles
- [x] 4.2 Verify that every case includes at least one parse profile and one emit profile with no `requires`
- [x] 4.3 Run the corpus-driven verification suite and confirm the refactored corpus still exercises default, strict, `y11safety`, and optional roundtrip behavior correctly
