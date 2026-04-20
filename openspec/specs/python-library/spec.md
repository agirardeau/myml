# Spec: Python Library

## Requirements

### Requirement: Library exposes a familiar Myml load and dump API

- Expose `load`, `loads`, `dump`, and `dumps`.
- Every entry point accepts `mode` with the values `default`, `strict`, and `y11safety`.
- Every entry point accepts `roundtrip` to enable formatting-preserving behavior.
- `loads` parses a Myml document string according to the selected mode.
- `loads` returns plain Python values or roundtrip-aware values based on `roundtrip`.
- `dumps` emits a Myml document according to the selected mode.
- `dumps` honors preserved formatting when the supplied values come from a roundtrip parse.
- Emit verification is driven by the checked-in conformance corpus.

### Requirement: Baseline installation has no required runtime dependencies

- The baseline package is usable with no required runtime dependencies beyond Python itself and the library package.
- Installing without extras is sufficient to import and use the parser and emitter.
- Optional extras or accelerators do not change baseline support or the public API contract.

### Requirement: Default mode conforms to the Myml language definition

- `default` mode accepts exactly the Myml language described in `docs/lang.md`.
- Unsupported YAML features are rejected.
- Invalid scalar forms are rejected.
- Parsing a document that is valid under `docs/lang.md` returns the corresponding Python representation graph.
- Scalar resolution follows the order defined by the Myml language definition.
- Parser results and raised errors for applicable corpus cases match the checked-in expectations.
- Corpus cases act as normative parser acceptance data for the library.

### Requirement: Default emission follows Myml serialization defaults

- In `default` mode, emitted documents follow the serialization defaults in `docs/lang.md` unless roundtrip preservation requires reusing existing source formatting.
- Emitting plain Python values writes UTF-8 Myml text using block-style containers.
- Emitting plain Python values uses unquoted keys and unquoted string scalars whenever the language definition permits them.
- Loading a document with `roundtrip=True` and dumping it without edits reproduces the original document exactly.
- The conformance corpus includes the expected emit result for that setting profile.

### Requirement: Roundtrip mode preserves document formatting metadata

- `roundtrip=True` preserves comments, whitespace, scalar style, and key order.
- Editing one scalar value in a roundtrip-loaded mapping preserves unchanged comments and key order.
- Unaffected surrounding whitespace and scalar styles remain preserved when the edit does not require reformatting.
- Roundtrip-loaded values retain enough metadata for the emitter to preserve formatting.
- Roundtrip-loaded values remain mutable by normal Python-style update operations.

### Requirement: Format-aware editing API

- Export `scalar()`, `mapping()`, and `sequence()` for durable node-local formatting metadata.
- Export `entry()` for durable entry-local formatting metadata such as pre-node comments and end-of-line comments.
- Export `as_format_aware()` to upgrade plain mappings and sequences into the same format-aware wrapper family used by `loads(..., roundtrip=True)`.
- Expose `insert()`, `move_before()`, `move_after()`, and `reorder()` on format-aware mappings for mutation-time placement.
- Keep ordinary item assignment as replace-or-append behavior without implicit placement semantics.
- Reject ambiguous `insert()` calls that specify both `before` and `after`.
- Require `reorder()` to receive a complete ordering of the mapping's keys.
- Preserve existing node-local and entry-local formatting metadata across replacement, insertion, and key-order changes.
- Honor explicitly supplied formatting metadata from these APIs when emitting dirty or newly inserted values, subject to `docs/lang.md` and the selected mode.
- Keep emitted output valid Myml, including flow-container restrictions and mode-specific quoting requirements.

#### Scenario: Caller uses the format-aware editing API

- A caller upgrades or loads a format-aware mapping.
- The caller inserts or replaces values with `scalar()`, `mapping()`, `sequence()`, or `entry()`, and changes key order with the placement APIs.
- The emitted document reflects the requested comments, scalar/container styles, and key order.
- The emitted document remains valid Myml for the selected mode.

### Requirement: Strict mode forbids unquoted string scalars

- `strict` mode enforces the strict-mode rules from `docs/lang.md`.
- Parsing an unquoted string scalar in `strict` mode raises an error.
- The strict-mode parse error states that quoted string scalars are required.
- Emitting string values in `strict` mode serializes those scalars in quoted form.
- Strict-mode output remains valid Myml.

### Requirement: Compatibility mode protects against YAML 1.1 ambiguities

- `y11safety` mode enforces the YAML 1.1 safety rules described in `docs/lang.md`.
- Unquoted ambiguous scalars such as `yes`, `no`, `on`, `off`, ISO-like date/time values, and other YAML 1.1-ambiguous forms are rejected in `y11safety` mode.
- Compatibility-mode parse errors identify the scalar as disallowed for that mode.
- Emitting a string whose plain form would be ambiguous to a YAML 1.1 parser uses a quoted form or another Myml-safe representation.
- Compatibility-mode output avoids YAML 1.1 ambiguity.

### Requirement: Corpus-driven verification covers library acceptance behavior

- Acceptance verification is driven by the checked-in conformance corpus.
- The Python library verification harness evaluates parser and emitter behavior against corpus expectations.
- Mode-sensitive parse and emit acceptance checks do not require a second approval dataset outside the corpus.

### Requirement: Parse errors are useful to callers

- Invalid input raises useful parse errors.
- Parse errors include line and column information when the location can be determined.
- Parse errors identify the relevant Myml rule or invalid syntax category.
