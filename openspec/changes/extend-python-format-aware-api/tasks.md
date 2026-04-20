## 1. Public API Surface

- [ ] 1.1 Add public `scalar()`, `mapping()`, `sequence()`, `entry()`, and `as_format_aware()` helpers in `libs/py-myml/src/myml`
- [ ] 1.2 Add the internal wrapper and coercion paths needed to distinguish node-local formatting metadata from entry-local formatting metadata
- [ ] 1.3 Add explicit entry accessors for existing mapping entries and sequence items without changing ordinary scalar read behavior

## 2. Format-Aware Mutation Behavior

- [ ] 2.1 Teach format-aware mappings and sequences to accept node constructors and `entry()` values during replacement and insertion
- [ ] 2.2 Implement `insert()`, `move_before()`, `move_after()`, and `reorder()` for format-aware mappings, including validation for ambiguous or incomplete placement requests
- [ ] 2.3 Preserve comments, styles, ordering metadata, and dirty tracking across replacement, insertion, and key-move operations

## 3. Emission, Tests, and Docs

- [ ] 3.1 Update emission so explicitly requested scalar, container, and entry formatting is honored for dirty and newly inserted values
- [ ] 3.2 Add library-level tests for constructor-based formatting, entry comments, `as_format_aware()`, and placement-aware mapping edits
- [ ] 3.3 Update Python library documentation to describe the format-aware editing API and how it relates to `roundtrip=True`
