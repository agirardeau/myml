# Proposal: Add Test Corpus

## Summary

Add a canonical conformance corpus for Myml together with a coverage matrix that
maps language rules to concrete test cases.

## Motivation

The language definition in `docs/lang.md` is now detailed enough to drive parser
and emitter behavior, but the repository does not yet provide an executable set
of examples that implementations can use for validation. Without a shared
corpus, different implementations can diverge on edge cases such as scalar
resolution, indentation validity, unsupported YAML features, and error
classification.

A repository-owned corpus gives the project a single source of truth for:

* valid documents and their expected representation
* invalid documents and their expected failure category
* coverage of the language specification, including optional modes
* the currently recommended filename convention for Myml source files

## Proposed Change

Create a versioned corpus structure for Myml conformance cases and a coverage
matrix that maps spec areas to test cases.

The change defines:

* a canonical on-disk structure for corpus cases
* metadata for valid and invalid cases
* a coverage index that tracks which language rules are exercised
* authoring guidance for adding new corpus cases over time
* contributor-facing documentation that recommends the `.yaml` extension for
  Myml files until a dedicated Myml extension is practical

## Scope

In scope:

* defining the test corpus file structure
* defining the expected artifacts for valid and invalid cases
* defining a coverage matrix format
* documenting the recommended `.yaml` extension for Myml files in a README or
  similar contributor-facing document
* seeding the corpus with an initial set of cases derived from `docs/lang.md`

Out of scope:

* implementing a parser or emitter
* implementing automated corpus runners for a specific language
* standardizing every parser's internal error wording
* changing `docs/lang.md` to define filename extension policy

## Success Criteria

This change is successful when:

* the repository contains a documented corpus structure for Myml conformance
* valid and invalid cases can be added without inventing new ad hoc conventions
* contributor-facing documentation recommends `.yaml` as the current extension
  for Myml files
* the initial corpus covers the main areas of `docs/lang.md`
* the coverage matrix makes gaps visible at a glance
