# Design: Add Test Corpus

## Overview

The corpus is organized around self-contained case directories rather than flat
filename conventions. Each case directory contains the source document, neutral
machine-readable expectations, and lightweight metadata.

This structure supports four goals:

* easy authoring by humans
* stable consumption by tooling
* clear traceability back to the language specification
* clear separation between Myml syntax under test and neutral test-oracle data

The corpus and its contributor-facing documentation recommend the `.yaml`
extension for Myml source files. This is a pragmatic convention based on current
editor and tooling support and does not change the language definition.

## Directory Layout

```text
corpus/
  README.md
  status.md
  cases/
    valid/
      <case-id>/
        input.yaml
        expected_parse.json
        expected_emit.json
        meta.json
    invalid/
      <case-id>/
        input.yaml
        error.json
        meta.json
```

## Case Model

Each case has a stable kebab-case identifier derived from the case directory
name.

### Valid Cases

A valid case directory contains:

* `input.yaml`: source text to parse as Myml
* `expected_parse.json`: canonical parsed value in a neutral data format
* `expected_emit.json`: canonical emitted-output expectation in a neutral data format
* `meta.json`: descriptive metadata

`expected_parse.json` stores the expected parsed structure in a canonical,
language-neutral form suitable for fixture comparison.

`expected_emit.json` stores the expected emitted output in a neutral envelope.
The current convention is an object containing a `format` field and a `text`
field. This keeps emitter testing distinct from parse-value testing.

### Invalid Cases

An invalid case directory contains:

* `input.yaml`: source text to reject as invalid Myml
* `error.json`: structured error expectation
* `meta.json`: descriptive metadata

`error.json` captures structured expectations such as:

* error code
* error category
* optional location metadata such as line and column
* optional notes about why the case is invalid

The design intentionally avoids requiring exact human-readable error strings.
That keeps the corpus portable across implementations while still testing the
important semantics.

## Why JSON for Control Files

JSON is used for metadata and expectations so the corpus does not require YAML
parsing for its own control data.

This avoids two problems:

* circular testing, where a buggy Myml implementation could agree with YAML-based
  fixtures for the wrong reasons
* unnecessary dependency on a second YAML-capable parser in test harnesses

The only YAML files in the corpus are Myml inputs under test.

## Metadata Format

`meta.json` captures lightweight descriptive information for both valid and
invalid cases. Recommended fields:

* `summary`
* `tags`
* `spec_refs`
* `modes`
* `notes`

The case identifier is derived from the directory name and is not duplicated
inside `meta.json`.

`spec_refs` links each case back to one or more spec sections or rule labels.
`modes` identifies whether the case applies to default mode, strict mode, YAML
1.1 Safety Mode, or multiple modes.

Per-case `meta.json` files are authoritative. Any coverage view or aggregate
index is derived from those files rather than treated as a separate canonical
source of metadata.

## Coverage Status

`corpus/status.md` records repo-level coverage notes such as covered areas,
known gaps, and follow-up work. It does not duplicate the per-case metadata.

This keeps the checked-in corpus source of truth local to each case while still
providing a human-readable place to track overall status.

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

### Why no canonical checked-in index

A checked-in aggregate index is convenient, but it duplicates the same metadata
already stored in the cases and creates drift risk. Keeping `meta.json` as the
only canonical case metadata keeps the source of truth simple.

### Why JSON for metadata and expectations

JSON is widely available across languages, unambiguous to parse, and suitable as
a neutral test oracle format. It also cleanly separates corpus-control data from
Myml syntax under test.

### Why `input.yaml` instead of `input.myml`

A dedicated `.myml` extension would communicate intent well, but current tools
and editors do not have built-in support for it. Using `.yaml` is the most
practical default today and reduces friction for contributors.

### Why structured errors instead of exact messages

Structured error expectations preserve portability across implementations and
allow better evolution of user-facing messages.

## Migration and Growth

The corpus layout is intended to be append-only for most changes. New language
features can add new cases and update the coverage notes without reorganizing
the existing corpus. If future tooling needs an aggregate index, it can be
derived from the per-case structure rather than driving the source of truth.
