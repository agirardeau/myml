## Why

`docs/lang.md` currently says comma thousands separators are not allowed, but
YAML numeric separators use underscores rather than commas. The numeric rules
also need a clearer distinction between plain decimals and scientific
notation: a single `0.` prefix should remain valid for plain fractional
decimals, while scientific notation should require a normalized coefficient
with `1 <= m < 10`. The parser contract and the corpus should describe and
validate the same behavior.

## What Changes

- Update the Myml numeric-language rules to reject underscore digit separators
  instead of describing unsupported comma separators.
- Clarify that plain fractional decimals may use exactly one leading zero
  before the decimal point, such as `0.5`.
- Require scientific notation to use a normalized coefficient with
  `1 <= m < 10`, rejecting forms such as `0.5e2` and `10e2`.
- Keep other leading-zero restrictions intact so integers like `00` and
  decimals like `00.5` remain invalid.
- Expand corpus coverage so valid and invalid cases demonstrate the accepted
  and rejected numeric forms explicitly.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `python-library`: update the accepted numeric forms in default parsing so the
  implementation contract matches the revised language definition, especially
  for scientific-notation normalization.
- `conformance-corpus`: add corpus expectations that prove underscore
  separators are rejected, `0.`-prefixed plain decimals are accepted, and
  non-normalized scientific notation is rejected.

## Impact

- `docs/lang.md`
- numeric parsing and validation behavior in the Python library
- corpus cases covering numeric acceptance and rejection
- corpus-backed parser verification for numeric edge cases
