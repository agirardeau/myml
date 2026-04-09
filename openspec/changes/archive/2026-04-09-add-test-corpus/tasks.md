# Tasks: Add Test Corpus

## 1. Define corpus structure

- [x] Create `corpus/README.md` describing the case layout and authoring rules
- [x] Document in `corpus/README.md` that `.yaml` is the recommended extension for Myml files until dedicated extension support is practical
- [x] Create `corpus/status.md` for repo-level coverage notes and known gaps
- [x] Define the schema-by-convention for per-case `meta.json`, `expected_parse.json`, `expected_emit.json`, and `error.json`

## 2. Seed valid corpus cases

- [x] Add valid cases covering core containers and scalar forms
- [x] Add valid cases covering comments and empty lines
- [x] Add valid cases covering numeric edge cases such as `0`, `0.5`, hex, and exponent notation
- [x] Add valid cases covering block scalar behavior and flow container behavior

## 3. Seed invalid corpus cases

- [x] Add invalid cases for unsupported YAML features such as anchors, tags, merge keys, and `~`
- [x] Add invalid cases for indentation violations and malformed collections
- [x] Add invalid cases for duplicate keys and disallowed unquoted characters
- [x] Add invalid cases for numeric rejection cases such as `-0`, `.5`, unsupported octal, and invalid casing

## 4. Add optional mode coverage

- [x] Add strict mode cases for unquoted string rejection
- [x] Add YAML 1.1 Safety Mode cases for ambiguous boolean, date/time, octal, and sexagesimal forms
- [x] Mark mode applicability in case metadata

## 5. Validate completeness

- [x] Cross-check the seeded corpus against `docs/lang.md`
- [x] Identify uncovered language rules and record them in `corpus/status.md`
- [x] Review the corpus structure for ease of use by future parser and emitter test runners
