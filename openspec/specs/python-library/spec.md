# Spec Delta: Python Library

## ADDED Requirements

### Requirement: Library exposes a familiar Myml load and dump API

The Python library MUST expose `load`, `loads`, `dump`, and `dumps` entry
points for parsing and emitting Myml documents. Each entry point MUST accept a
`mode` option with the values `default`, `strict`, and `y11safety`, and
MUST accept a `roundtrip` option that enables formatting-preserving behavior.

#### Scenario: Caller parses from text

- **WHEN** a caller passes a Myml document string to `loads`
- **THEN** the library parses the document according to the selected mode
- **AND** the library returns either plain Python values or roundtrip-aware
  values based on the `roundtrip` option

#### Scenario: Caller emits to text

- **WHEN** a caller passes Python values to `dumps`
- **THEN** the library emits a Myml document according to the selected mode
- **AND** the emitter honors roundtrip-preserved formatting when the supplied
  values came from a roundtrip parse
- **AND** verification of that emitted output is driven by the checked-in
  conformance corpus

### Requirement: Baseline installation has no required runtime dependencies

The Python library MUST be usable without any required external runtime
dependencies beyond Python itself and the library package, while still allowing
future optional extras.

#### Scenario: Caller installs the baseline package

- **WHEN** a user installs the library without opting into any extras
- **THEN** they can import and use the parser and emitter without installing a
  separate runtime dependency or native extension

#### Scenario: Project adds an optional accelerator later

- **WHEN** the project introduces an optional performance-oriented extra
- **THEN** the baseline install remains supported without that extra
- **AND** the public API behavior remains defined independently of whether the
  optional extra is present

### Requirement: Default mode conforms to the Myml language definition

In `default` mode, the library MUST accept exactly the Myml language described
in `docs/lang.md` and MUST reject unsupported YAML features and invalid scalar
forms.

#### Scenario: Parser matches corpus expectations

- **WHEN** a caller parses an input from the checked-in valid or invalid
  conformance corpus in the applicable mode
- **THEN** the parser result or raised error matches the expectations recorded
  for that corpus case
- **AND** corpus cases act as normative parser acceptance data for the library

#### Scenario: Supported Myml input is accepted

- **WHEN** a caller parses a document that is valid under `docs/lang.md`
- **THEN** the library returns the corresponding Python representation graph
- **AND** scalar resolution follows the order defined by the Myml language
  definition

#### Scenario: Unsupported YAML input is rejected

- **WHEN** a caller parses input that uses a YAML construct outside the Myml
  language definition
- **THEN** the library raises an error
- **AND** the error identifies the unsupported construct or malformed syntax as
  the cause

### Requirement: Default emission follows Myml serialization defaults

In `default` mode, emitted documents MUST follow the serialization defaults in
`docs/lang.md` unless roundtrip preservation requires reusing existing source
formatting.

#### Scenario: Caller emits plain Python values in default mode

- **WHEN** a caller emits values that were not loaded in roundtrip mode
- **THEN** the library writes UTF-8 Myml text using block-style containers
- **AND** the library uses unquoted keys and unquoted string scalars whenever
  permitted by the language definition

#### Scenario: Caller emits roundtrip values without edits

- **WHEN** a caller loads a document with `roundtrip=True` and immediately dumps
  it without modifying the returned values
- **THEN** the emitted text matches the original document exactly
- **AND** the corpus contains the corresponding expected emit result for that
  setting profile

### Requirement: Roundtrip mode preserves document formatting metadata

When `roundtrip=True`, the library MUST preserve comments, whitespace, scalar
style, and key order so callers can edit documents without losing unaffected
source formatting.

#### Scenario: Caller edits one value in a roundtrip document

- **WHEN** a caller loads a mapping with `roundtrip=True`, changes one scalar
  value, and dumps the result
- **THEN** unchanged comments and key order are preserved
- **AND** unaffected surrounding whitespace and scalar styles remain preserved
  where the edit does not require reformatting

#### Scenario: Caller reads formatting-preserving values

- **WHEN** a caller loads a document with `roundtrip=True`
- **THEN** the returned values retain enough metadata for the emitter to
  preserve formatting
- **AND** the values remain mutable by normal Python-style update operations

### Requirement: Strict mode forbids unquoted string scalars

In `strict` mode, the library MUST enforce the strict-mode rules from
`docs/lang.md`.

#### Scenario: Strict mode rejects unquoted string input

- **WHEN** a caller parses a document in `strict` mode that contains an
  unquoted string scalar
- **THEN** the library raises an error
- **AND** the error indicates that strict mode requires quoted string scalars

#### Scenario: Strict mode quotes emitted strings

- **WHEN** a caller emits string values in `strict` mode
- **THEN** the library serializes those string scalars in quoted form
- **AND** the emitted document remains valid Myml

### Requirement: Compatibility mode protects against YAML 1.1 ambiguities

In `y11safety` mode, the library MUST enforce the YAML 1.1 safety rules
described in `docs/lang.md` under YAML 1.1 Safety Mode.

#### Scenario: Compatibility mode rejects ambiguous unquoted input

- **WHEN** a caller parses a document in `y11safety` mode that contains
  an unquoted scalar such as `yes`, `no`, `on`, `off`, an ISO-like date/time,
  or another YAML 1.1-ambiguous form
- **THEN** the library raises an error
- **AND** the error indicates that the scalar is disallowed in compatibility
  mode

#### Scenario: Compatibility mode emits safe strings

- **WHEN** a caller emits a string value in `y11safety` mode whose plain
  form would be ambiguous to a YAML 1.1 parser
- **THEN** the library emits that value in a quoted form or another Myml-safe
  representation
- **AND** the emitted output avoids YAML 1.1 ambiguity

### Requirement: Corpus-driven verification covers library acceptance behavior

The library's acceptance verification MUST be driven by the checked-in
conformance corpus rather than a separate Python-only expectation format.

#### Scenario: Harness verifies parse and emit behavior

- **WHEN** the Python library verification harness runs
- **THEN** it evaluates parser and emitter behavior against corpus expectations
- **AND** it does not require a second approval dataset outside the corpus for
  mode-sensitive parse and emit acceptance checks

### Requirement: Parse errors are useful to callers

The library MUST raise useful parse errors for invalid input.

#### Scenario: Error reports source location

- **WHEN** a caller parses malformed input
- **THEN** the raised error includes line and column information when that
  location can be determined
- **AND** the error message identifies the relevant Myml rule or invalid syntax
  category
