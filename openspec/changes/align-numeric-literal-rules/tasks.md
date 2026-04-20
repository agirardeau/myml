## 1. Align numeric rules

- [x] 1.1 Update `docs/lang.md` to reject underscore numeric separators and to
      state that only plain fractional decimals may use a single `0.` prefix
- [x] 1.2 Tighten numeric parsing so scientific notation accepts only
      normalized coefficients where `1 <= m < 10`
- [x] 1.3 Preserve existing rejection of malformed leading-zero forms such as
      `.5`, `00.5`, `0.5e2`, and `10e2` with useful parse errors

## 2. Refresh corpus coverage

- [x] 2.1 Update valid numeric corpus coverage to include plain fractional
      decimals and normalized scientific notation examples
- [x] 2.2 Add or update invalid corpus cases for underscore separators in
      numeric tokens
- [x] 2.3 Add or update invalid corpus cases for non-normalized scientific
      notation coefficients

## 3. Verify corpus-backed behavior

- [x] 3.1 Run the corpus-backed Python tests covering numeric parsing and emit
      expectations
- [x] 3.2 Confirm the updated corpus expectations match the revised language
      definition and parser behavior
