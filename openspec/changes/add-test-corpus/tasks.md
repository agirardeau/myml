# Tasks: Add Test Corpus

## 1. Define corpus structure

- [ ] Create `corpus/README.md` describing the case layout and authoring rules
- [ ] Document in `corpus/README.md` that `.yaml` is the recommended extension for Myml files until dedicated extension support is practical
- [ ] Create `corpus/index.yaml` as the coverage matrix format
- [ ] Define the schema-by-convention for `meta.yaml`, `expected.yaml`, and `error.yaml`

## 2. Seed valid corpus cases

- [ ] Add valid cases covering core containers and scalar forms
- [ ] Add valid cases covering comments and empty lines
- [ ] Add valid cases covering numeric edge cases such as `0`, `0.5`, hex, and exponent notation
- [ ] Add valid cases covering block scalar behavior and flow container behavior

## 3. Seed invalid corpus cases

- [ ] Add invalid cases for unsupported YAML features such as anchors, tags, merge keys, and `~`
- [ ] Add invalid cases for indentation violations and malformed collections
- [ ] Add invalid cases for duplicate keys and disallowed unquoted characters
- [ ] Add invalid cases for numeric rejection cases such as `-0`, `.5`, unsupported octal, and invalid casing

## 4. Add optional mode coverage

- [ ] Add strict mode cases for unquoted string rejection
- [ ] Add YAML 1.1 Safety Mode cases for ambiguous boolean, date/time, octal, and sexagesimal forms
- [ ] Mark mode applicability in case metadata and the coverage index

## 5. Validate completeness

- [ ] Cross-check `corpus/index.yaml` against `docs/lang.md`
- [ ] Identify any uncovered language rules and add TODO coverage entries or new cases
- [ ] Review the corpus structure for ease of use by future parser and emitter test runners
