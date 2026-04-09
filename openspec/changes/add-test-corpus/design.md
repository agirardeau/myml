# Design: Add Test Corpus

## Overview

The corpus is organized around self-contained case directories rather than flat
filename conventions. Each case directory contains the source document, machine-
readable expectations, and lightweight metadata. A separate coverage index maps
spec sections and rules to case identifiers.

This structure supports three goals:

* easy authoring by humans
* stable consumption by tooling
* clear traceability back to the language specification

The corpus and its contributor-facing documentation recommend the `.yaml`
extension for Myml source files. This is a pragmatic convention based on current
editor and tooling support and does not change the language definition.

## Directory Layout

```text
corpus/
  README.md
  index.yaml
  cases/
    valid/
      <case-id>/
        input.yaml
        expected.yaml
        meta.yaml
    invalid/
      <case-id>/
        input.yaml
        error.yaml
        meta.yaml
```

## Case Model

Each case has a stable kebab-case identifier.

### Valid Cases

A valid case directory contains:

* `input.yaml`: source text to parse as Myml
* `expected.yaml`: canonical expected value in a language-neutral form
* `meta.yaml`: descriptive metadata

`expected.yaml` stores the expected parsed structure in a canonical serialized
form suitable for fixture comparison. It is intended to represent the same YAML
representation graph described by the language specification, using a stable
encoding chosen by the repository.

### Invalid Cases

An invalid case directory contains:

* `input.yaml`: source text to reject as invalid Myml
* `error.yaml`: structured error expectation
* `meta.yaml`: descriptive metadata

`error.yaml` captures structured expectations such as:

* error code
* error category
* optional location metadata such as line and column
* optional notes about why the case is invalid

The design intentionally avoids requiring exact human-readable error strings.
That keeps the corpus portable across implementations while still testing the
important semantics.

## Metadata Format

`meta.yaml` captures lightweight descriptive information for both valid and
invalid cases. Recommended fields:

* `id`
* `summary`
* `tags`
* `spec_refs`
* `modes`
* `notes`

`spec_refs` links each case back to one or more spec sections or rule labels.
`modes` identifies whether the case applies to default mode, strict mode, YAML
1.1 Safety Mode, or multiple modes.

## Coverage Matrix

`corpus/index.yaml` acts as the coverage matrix.

It records:

* the list of corpus cases
* status of each case as valid or invalid
* spec references covered by each case
* optional gaps or TODO markers for spec areas without cases yet

This index is the main place to answer questions like:

* Which cases exercise number parsing?
* Which cases cover strict mode?
* Which rules still have no test coverage?

## Documentation

`corpus/README.md` documents the corpus layout, authoring conventions, and the
recommended `.yaml` extension for Myml source files.

The extension recommendation is operational rather than normative. It exists so
contributors, editors, and tools can converge on one practical convention while
Myml-specific extension support is absent or immature.

## Initial Coverage Areas

The first seeded corpus should cover at least:

* block mappings and sequences
* flow containers and their scalar-only restriction
* quoted, unquoted, and block scalar strings
* numeric forms and numeric rejection cases
* boolean and null resolution
* duplicate keys
* indentation rules
* unsupported YAML features such as anchors, tags, merge keys, and `~`
* strict mode behavior
* YAML 1.1 Safety Mode behavior

## Tradeoffs

### Why per-case directories

Per-case directories are slightly more verbose than flat files, but they make it
much easier to attach metadata, expected outputs, and future extensions without
compressing meaning into filenames.

### Why `input.yaml` instead of `input.myml`

A dedicated `.myml` extension would communicate intent well, but current tools
and editors do not have built-in support for it. Using `.yaml` is the most
practical default today and reduces friction for contributors.

### Why `expected.yaml` instead of JSON

The language targets YAML compatibility, and YAML is more natural for expressing
nested expected structures while still being easy for tooling to parse.

### Why structured errors instead of exact messages

Structured error expectations preserve portability across implementations and
allow better evolution of user-facing messages.

## Migration and Growth

The corpus layout is intended to be append-only for most changes. New language
features can add new cases and new coverage entries without reorganizing the
existing corpus. If future tooling needs a generated flat format, it can be
derived from the per-case structure rather than driving the source of truth.
