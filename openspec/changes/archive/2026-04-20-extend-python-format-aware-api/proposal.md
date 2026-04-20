## Why

The Python library already preserves formatting metadata internally, but its
public mutation API only accepts plain values. That makes it impossible for
callers to intentionally inject formatting choices such as block-scalar style,
pre-node comments, end-of-line comments, or key placement when they edit a
document.

## What Changes

- Extend the Python library's public roundtrip-editing API with durable
  format-aware constructors `scalar()`, `mapping()`, and `sequence()` for
  callers who want to create values with explicit formatting metadata.
- Add a durable `entry()` wrapper so callers can attach entry-local formatting
  such as pre-node comments and end-of-line comments without overloading scalar
  values with container-specific metadata.
- Add mutation-time placement operations such as `insert()`, `move_before()`,
  `move_after()`, and `reorder()` so callers can control mapping order and
  structural edits directly instead of relying on append-only updates.
- Clarify the roundtrip-editing model so format-aware values may be created
  from parsed roundtrip data or injected into existing mappings and sequences
  that were loaded or upgraded for formatting-aware edits.
- Add conformance coverage for formatting-aware construction and placement
  operations, including injected block-scalar style and comment preservation
  around structural edits.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `python-library`: Extend the public formatting-preserving editing contract to
  support explicit format-aware value construction, entry-local formatting, and
  mutation-time placement operations.

## Impact

- Changes the public Python API exposed from `libs/py-myml`.
- Affects the roundtrip wrapper model, node/entry construction helpers, and
  mutation methods for mappings and sequences.
- Requires emitter and change-tracking behavior to honor injected formatting
  metadata, not only formatting metadata parsed from source text.
- Adds corpus and library-test coverage for formatting-aware edits and
  ordering-sensitive mutations.
