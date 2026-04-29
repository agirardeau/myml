## MODIFIED Requirements

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
