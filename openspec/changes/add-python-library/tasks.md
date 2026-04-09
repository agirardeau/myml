# Tasks: Add Python Library

## 1. Package scaffolding

- [ ] 1.1 Add Python packaging metadata under `libs/py-myml` and create the initial `src/myml` module layout
- [ ] 1.2 Add public `load`, `loads`, `dump`, and `dumps` entry points with `mode` and `roundtrip` options
- [ ] 1.3 Keep the baseline package usable with no required runtime dependencies while preserving room for future optional extras
- [ ] 1.4 Remove `prompts/python.md` and ensure project documentation points to `docs/lang.md` and `openspec/` artifacts as the source of truth

## 2. Corpus contract and fixtures

- [ ] 2.1 Update corpus documentation and schema-by-convention so valid cases can define emit expectations for multiple setting profiles
- [ ] 2.2 Add or revise corpus cases that cover default, roundtrip, strict, and `y11safety` emission behavior
- [ ] 2.3 Keep mode-sensitive parse rejection coverage in the corpus using applicable valid and invalid cases

## 3. Default-mode parser and emitter

- [ ] 3.1 Implement default-mode parsing for mappings, sequences, scalars, comments, and empty lines according to `docs/lang.md`
- [ ] 3.2 Implement useful parse errors for malformed input, unsupported YAML features, duplicate keys, and invalid scalar forms
- [ ] 3.3 Implement default-mode emission using Myml serialization defaults for block containers and quotable scalars

## 4. Roundtrip preservation

- [ ] 4.1 Add internal syntax-tree and metadata structures that retain comments, whitespace, scalar style, and key order
- [ ] 4.2 Return roundtrip-aware values when `roundtrip=True` and keep plain Python values as the default behavior
- [ ] 4.3 Implement dump behavior that preserves exact text for unchanged roundtrip documents and preserves unaffected formatting around edited nodes

## 5. Mode handling

- [ ] 5.1 Implement `strict` mode parsing and emission rules for quoted string enforcement
- [ ] 5.2 Implement `y11safety` mode parsing and emission rules for YAML 1.1-ambiguous scalars
- [ ] 5.3 Add validation so unsupported mode names fail with a clear caller-facing error

## 6. Verification

- [ ] 6.1 Build a Python verification harness that runs parser and emitter behavior against the checked-in conformance corpus
- [ ] 6.2 Verify roundtrip, default, strict, and `y11safety` acceptance behavior from corpus expectations rather than separate Python-specific fixtures
- [ ] 6.3 Document the Python library API, its mode semantics, and how corpus-driven verification maps to the library behavior
