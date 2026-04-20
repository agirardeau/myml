## Context

Myml numeric behavior is defined normatively in `docs/lang.md`, enforced by the
Python parser, and regression-tested through the conformance corpus. Today the
documentation mentions comma thousands separators even though YAML-style digit
separators use underscores. The documentation also describes the leading-zero
exception only in terms of decimals beginning with `0.`, which leaves
scientific notation normalization underspecified. The current parser regex also
accepts non-normalized exponent forms such as `0.5e2` and `10e2`, so the
implementation contract needs to become stricter rather than broader.

This change is a cross-cutting spec-alignment update rather than a data-model
change. The implementation work should keep the language, parser contract, and
corpus fixtures in sync without widening numeric support beyond the requested
cases.

## Goals / Non-Goals

**Goals:**

- align the language definition with YAML-relevant numeric separator wording
- define the fractional leading-zero rule clearly for plain decimals
- require scientific notation coefficients to satisfy `1 <= m < 10`
- preserve existing rejection of integers and fractional forms with multiple
  leading zeroes
- add corpus coverage that proves the accepted and rejected numeric forms

**Non-Goals:**

- adding support for YAML digit separators
- allowing leading-dot forms such as `.5` or `.5e2`
- changing emission style beyond what is needed to validate existing numeric
  semantics
- changing numeric handling for hex, infinity, NaN, or integer forms

## Decisions

### Describe unsupported separators in YAML terms

The language definition will say underscore separators are not supported for
numbers. This matches YAML syntax more directly than the current comma-based
wording and gives the corpus a concrete lexical form to reject.

Alternative considered:

- keep the wording as "comma thousands separators are not allowed"
  Rejected because it documents a formatting convention Myml never supported,
  but it misses the YAML feature contributors are most likely to try.

### Normalize scientific-notation coefficients

The leading-zero exception will remain specific to plain fractional decimals.
Scientific notation will require a normalized coefficient whose magnitude is at
least `1` and less than `10`. That keeps `0.5` valid as a plain decimal while
rejecting exponent forms such as `0.5e2`, `.5e2`, `10e2`, and `00.5e2`.

Alternative considered:

- allow `0.`-prefixed coefficients in scientific notation
  Rejected because it would preserve an underspecified and non-normalized
  exponent form that conflicts with the stated `1 <= m < 10` rule.

### Validate the rule with focused corpus cases

The corpus update will keep one canonical valid numeric case for accepted forms
and add focused invalid cases for unsupported separators and non-normalized
scientific notation. Keeping these behaviors in narrow cases makes failures
easier to diagnose than folding every boundary case into one large fixture.

Alternative considered:

- extend only the existing `numeric-forms` and `leading-dot-decimal` cases
  Rejected because separator rejection and scientific-notation normalization
  edge cases are
  easier to reason about when they have dedicated, single-purpose fixtures.

## Risks / Trade-offs

- [Spec language remains ambiguous] -> Update both the prose examples and the
  leading-zero restriction bullets so the accepted and rejected forms are
  explicit.
- [Corpus fixtures drift from implementation reality] -> Add both valid and
  invalid cases that exercise plain-decimal acceptance and scientific-notation
  rejection paths.
- [Contributors misread the change as supporting digit separators] -> Keep the
  proposal and spec language explicit that underscores remain invalid.
- [Existing parser behavior differs from the new contract at the edges] ->
  Tighten the parser's exponent regex and lexical checks against the new corpus
  cases during implementation.
