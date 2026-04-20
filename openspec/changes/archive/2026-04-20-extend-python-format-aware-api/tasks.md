## 1. Public API Surface

- [x] 1.1 Add public `scalar()`, `mapping()`, `sequence()`, `entry()`, and `as_format_aware()` helpers in `libs/py-myml/src/myml`
- [x] 1.2 Add the internal wrapper and coercion paths needed to distinguish node-local formatting metadata from entry-local formatting metadata
- [x] 1.3 Add explicit entry accessors for existing mapping entries and sequence items without changing ordinary scalar read behavior

## 2. Format-Aware Mutation Behavior

- [x] 2.1 Teach format-aware mappings and sequences to accept node constructors and `entry()` values during replacement and insertion
- [x] 2.2 Implement `insert()`, `move_before()`, `move_after()`, and `reorder()` for format-aware mappings, including validation for ambiguous or incomplete placement requests
- [x] 2.3 Preserve comments, styles, ordering metadata, and dirty tracking across replacement, insertion, and key-move operations

## 3. Emission, Tests, and Docs

- [x] 3.1 Update emission so explicitly requested scalar, container, and entry formatting is honored for dirty and newly inserted values
- [x] 3.2 Add library-level tests for constructor-based formatting, entry comments, `as_format_aware()`, and placement-aware mapping edits
- [x] 3.3 Update Python library documentation to describe the format-aware editing API and how it relates to `roundtrip=True`
