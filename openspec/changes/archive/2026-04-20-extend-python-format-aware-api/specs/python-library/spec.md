# Spec Delta: Python Library

## ADDED Requirements

### Requirement: Format-aware editing API

- Export `scalar()`, `mapping()`, and `sequence()` for durable node-local
  formatting metadata.
- Export `entry()` for durable entry-local formatting metadata such as
  pre-node comments and end-of-line comments.
- Export `as_format_aware()` to upgrade plain mappings and sequences into the
  same format-aware wrapper family used by `loads(..., roundtrip=True)`.
- Expose `insert()`, `move_before()`, `move_after()`, and `reorder()` on
  format-aware mappings for mutation-time placement.
- Keep ordinary item assignment as replace-or-append behavior without implicit
  placement semantics.
- Reject ambiguous `insert()` calls that specify both `before` and `after`.
- Require `reorder()` to receive a complete ordering of the mapping's keys.
- Preserve existing node-local and entry-local formatting metadata across
  replacement, insertion, and key-order changes.
- Honor explicitly supplied formatting metadata from these APIs when emitting
  dirty or newly inserted values, subject to `docs/lang.md` and the selected
  mode.
- Keep emitted output valid Myml, including flow-container restrictions and
  mode-specific quoting requirements.

#### Scenario: Caller uses the format-aware editing API

- A caller upgrades or loads a format-aware mapping.
- The caller inserts or replaces values with `scalar()`, `mapping()`,
  `sequence()`, or `entry()`, and changes key order with the placement APIs.
- The emitted document reflects the requested comments, scalar/container
  styles, and key order.
- The emitted document remains valid Myml for the selected mode.
