# Spec: Serde Myml Rust Library

## Requirements

### Requirement: Crate provides a Serde-based Myml API

- The repository contains a Rust library crate at `libs/serde-myml` named `serde-myml`.
- The crate supports parsing Myml into any compatible type implementing `serde::Deserialize` and emitting Myml from any compatible type implementing `serde::Serialize`.
- The crate exposes `from_str`, `from_reader`, `to_string`, and `to_writer` entry points, plus a public dynamic `Value` type that implements `Serialize` and `Deserialize`.
- The crate exposes a public `Mode` enum with `Standard` and `Strict` variants. `from_str`, `from_reader`, `to_string`, and `to_writer` use `Standard` mode by default; corresponding `from_str_with_mode`, `from_reader_with_mode`, `to_string_with_mode`, and `to_writer_with_mode` functions accept a `Mode` argument. The mode is selected per call, not by a Cargo feature flag.
- The crate does not provide roundtrip formatting preservation or a format-aware editing API.

### Requirement: Parsing follows the Myml language definition

- In `standard` mode, parsing accepts Myml as defined in `docs/lang.md`, subject to the numeric representation limit below.
- In `strict` mode, parsing rejects unquoted string scalars and reports that quoted string scalars are required.
- Parsing rejects unsupported YAML features, invalid scalar forms, non-string mapping keys, and duplicate mapping keys.
- Scalar resolution follows the order in `docs/lang.md`.
- YAML 1.1-ambiguous plain scalars are strings unless they match a supported Myml scalar form.
- Parsed mappings in `Value` are ordered by key, regardless of source order.
- Invalid input produces useful errors with line and column information when available and an indication of the relevant rule or syntax category.

### Requirement: Dynamic numbers use bounded Rust types

- `Value` represents integers with `i64` or `u64` and non-integer numbers with `f64`.
- The number representation supports positive infinity, negative infinity, and NaN, including Myml's `.inf`, `-.inf`, and `.nan` literals.
- Parsing an integer outside the `i64` and `u64` ranges returns a numeric range error rather than silently rounding or converting it to a string or floating-point value.
- Deserialization into a requested Rust numeric type returns an error when the parsed number cannot be represented by that type.
- Emission of an unsupported numeric value returns an error rather than emitting invalid Myml or silently changing its value.

### Requirement: Emission follows Myml serialization defaults

- Emitted text is valid Myml in the selected mode and follows the serialization defaults in `docs/lang.md`.
- Emission uses UTF-8 text, block-style containers, and compact block mappings within sequences.
- Mapping entries are emitted in lexicographic key order by default, including when the caller's map or struct has another iteration order.
- Keys and string scalars are unquoted when Myml permits them in `standard` mode.
- String scalars are quoted in `strict` mode.
- Infinity and NaN are emitted using the supported lowercase Myml literals.
- Serialization rejects mapping keys that cannot be represented as Myml string keys.

### Requirement: Corpus-driven verification

- The crate's parser and emitter are verified against applicable baseline profiles in the checked-in conformance corpus.
- Roundtrip profiles requiring formatting preservation do not apply to this crate.
- Numeric range limitations are documented and tested separately where a corpus input exceeds the supported representation.
