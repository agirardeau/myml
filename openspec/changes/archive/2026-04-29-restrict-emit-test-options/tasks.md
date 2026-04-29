## 1. Tighten the corpus contract

- [x] 1.1 Update `corpus/README.md` to document baseline per-mode emit profiles plus `options.roundtrip` as the only supported non-baseline emit-test option
- [x] 1.2 Update the Python corpus harness in `libs/py-myml/tests/test_corpus.py` to reject unsupported emit-profile options and to keep `roundtrip` as the only optional emit-test capability

## 2. Remove the scripted edit corpus case

- [x] 2.1 Remove the `roundtrip_edit_note` emit profile from `corpus/cases/comments-and-empty-lines/meta.json`
- [x] 2.2 Remove the now-unused `corpus/cases/comments-and-empty-lines/expected_emit_roundtrip_edit_note.yaml` fixture

## 3. Re-verify corpus-backed expectations

- [x] 3.1 Run the corpus-backed Python tests and confirm the remaining emit profiles still pass under the tightened contract
- [x] 3.2 Confirm no checked-in corpus case still relies on emit options beyond baseline mode selection and `options.roundtrip`
