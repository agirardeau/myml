# Spec: Conformance Corpus
## Requirements
### Requirement: Canonical Conformance Corpus

- The repository contains a canonical conformance corpus for Myml.
- Each case representing one Myml input document lives under `corpus/cases/<case-id>/`.
- The input under test is stored in `input.yaml`.
- Successful parse outcomes reference a canonical `expected_node_graph.json` artifact.
- Successful emit outcomes reference one or more `expected_emit_{PROFILE}.yaml` files.
- `meta.json` describes parse and emit profiles for the case.

### Requirement: Per-case metadata is authoritative

- Per-case `meta.json` files are the authoritative source of corpus metadata and profile expectations.
- Tooling discovers corpus cases and covered rules from the per-case `meta.json` files.
- No separate checked-in aggregate metadata file is required for correctness.
- `meta.json` contains `parse_profiles` and `emit_profiles` keyed by profile id.
- Each parse profile declares `modes`.
- Each emit profile declares `mode`.
- Either kind of profile may declare `requires`.
- Parse and emit failures are represented as structured JSON data in `meta.json`.
- Emit profile metadata is discovered from `meta.json`.
- Expected emitted Myml text is read from the referenced `expected_emit_{PROFILE}.yaml` files.
- Descriptive case metadata remains in the same `meta.json` file.

### Requirement: Test suite metadata does not require correct YAML parser to access

- All control files use JSON rather than YAML.

### Requirement: Corpus layout supports growth

- New cases can be added without restructuring fixtures or existing cases.

### Requirement: Parse profiles cover supported modes

- Each case defines parse expectations that cover every supported parse mode exactly once.
- Each parse profile declares `modes` as either an explicit array of supported mode names or the scalar value `"all"`.
- The set of parse profiles covers every supported parse mode exactly once.
- If one parse profile uses `"all"`, no other parse profile is present.
- A successful parse profile declares `expect_node_graph`.
- A successful parse profile references the case's canonical `expected_node_graph.json`.
- A successful parse profile does not declare `expect_error`.
- A failed parse profile declares `expect_error`.
- A failed parse profile stores the error expectation inline in `meta.json`.
- A failed parse profile does not declare `expect_node_graph`.

### Requirement: Emit profiles express serialization expectations

- Each case defines zero or more named emit profiles for the case's semantic graph.
- Every emit profile declares top-level `mode`.
- A successful emit profile declares `expect_output` referencing `expected_emit_{PROFILE}.yaml`.
- A successful emit profile does not declare `expect_error`.
- A failed emit profile declares `expect_error` inline in `meta.json`.
- A failed emit profile does not declare `expect_output`.
- An emit profile without `options` is a baseline emit profile for its mode.
- `options` is supported only for `roundtrip`.
- A roundtrip emit profile declares `options.roundtrip: true`.
- A roundtrip emit profile declares `requires: ["roundtrip"]`.
- No other emit option keys or values are part of the corpus contract.

### Requirement: Optional feature gating is explicit

- Parse and emit profiles support optional feature requirements through a `requires` array.
- Profiles that depend on optional implementation features declare those features in `requires`.
- Harnesses can use `requires` to decide whether a profile is relevant.
- Each case includes at least one parse profile with no `requires`.
- Each case includes at least one emit profile with no `requires`.

### Requirement: Language boundary cases are explicit in the corpus

- The corpus includes focused cases for language boundaries defined by `docs/lang.md`, including:
  - Scalar forms and scalar resolution behavior
  - Block-style and flow-style container rules
  - Quoted, unquoted, and block scalar string behavior
  - Comments and empty-line handling
  - Unsupported YAML features and other invalid inputs
  - Mode-specific behavior such as `strict` and `y11safety`

