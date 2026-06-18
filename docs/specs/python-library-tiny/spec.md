# Spec: Tiny Python Library

## Requirements

### Requirement: Tiny library exposes a read-only Myml API

- The repository contains a Python library at `libs/py-myml-tiny`.
- The tiny library exposes `load` and `loads` for reading Myml.
- The tiny library parses Myml document strings and text streams into plain Python values.
- The tiny library supports the `standard` and `strict` parser modes.
- The tiny library exposes caller-facing `MymlError`, `ParseError`, and `ModeError` error classes.
- The tiny library does not expose `dump`, `dumps`, roundtrip metadata, formatting-aware editing APIs, or any other emitter API.

### Requirement: Tiny library is dependency-free at runtime

- Installing the tiny library requires no runtime dependencies beyond Python itself and the library package.
- The baseline installation is sufficient to import and use `load` and `loads`.
- The tiny library does not depend on the full `py-myml` implementation.

### Requirement: Tiny library conforms to Myml parse behavior

- In `standard` mode, the tiny library accepts exactly the Myml language described in `docs/lang.md`.
- In `strict` mode, the tiny library enforces strict-mode parse restrictions from `docs/lang.md`.
- Unsupported YAML features are rejected.
- Invalid scalar forms are rejected.
- Parsing a valid document returns the corresponding plain Python representation graph.
- Parser results and raised errors for applicable corpus parse profiles match the checked-in expectations.
- The checked-in conformance corpus acts as normative parser acceptance data for the tiny library.

### Requirement: Tiny library remains implementation-small

- The reader implementation is kept in a single Python source file unless the single-file shape becomes impractical.
- The source file contains the parser and public read API.
- Tests, packaging metadata, and documentation may live outside the single implementation source file.

### Requirement: Parse errors are useful to callers

- Invalid input raises useful parse errors.
- Parse errors include line and column information when the location can be determined.
- Parse errors identify the relevant Myml rule or invalid syntax category.
