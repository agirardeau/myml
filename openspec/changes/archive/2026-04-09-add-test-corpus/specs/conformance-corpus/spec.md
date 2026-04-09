# Spec Delta: Conformance Corpus

## ADDED Requirements

### Requirement: Canonical Conformance Corpus

The repository contains a canonical conformance corpus for Myml.

#### Scenario: Valid case is represented canonically

- **WHEN** a test case represents valid Myml input
- **THEN** the corpus stores the input document together with a machine-readable
  parse expectation
- **AND** the corpus stores a machine-readable emit expectation
- **AND** the case includes metadata describing the rule areas it covers

#### Scenario: Invalid case is represented canonically

- **WHEN** a test case represents invalid Myml input
- **THEN** the corpus stores the input document together with a machine-readable
  expected error description
- **AND** the case includes metadata describing the rule areas it covers

### Requirement: Per-Case Metadata Is Authoritative

Per-case `meta.json` files are the authoritative source of corpus metadata.

#### Scenario: Tooling needs a case catalog

- **WHEN** tooling needs to discover corpus cases or their covered rules
- **THEN** it derives that information from the per-case `meta.json` files
- **AND** no separate checked-in aggregate metadata file is required for correctness

### Requirement: JSON Control Files Separate the Oracle from the Syntax Under Test

Corpus control files use JSON rather than YAML.

#### Scenario: Harness reads expected parse or error data

- **WHEN** a test harness reads corpus metadata or expectations
- **THEN** it reads JSON control files rather than YAML control files
- **AND** the Myml input under test remains isolated in `input.yaml`

### Requirement: Coverage Status Is Documented

The repository documents overall corpus coverage status and known gaps.

#### Scenario: Contributor reviews remaining coverage work

- **WHEN** a contributor checks the corpus status
- **THEN** they can see covered areas and known gaps without inspecting every case
- **AND** that status documentation does not replace per-case metadata as the source of truth

### Requirement: Corpus Layout Supports Growth

The corpus layout supports incremental growth without changing existing case
identifiers or rewriting earlier fixtures.

#### Scenario: New case is added

- **WHEN** a contributor adds a new corpus case
- **THEN** the case can be added in its own stable directory with metadata and
  expected output artifacts
- **AND** repo-level coverage notes can be updated without restructuring
  existing cases

### Requirement: Corpus Documentation Recommends a Practical Extension

The repository documents a recommended filename extension for Myml source files.

#### Scenario: Contributor chooses a filename for Myml input

- **WHEN** a contributor creates a corpus input file or example Myml document
- **THEN** the repository documentation recommends the `.yaml` extension
- **AND** the recommendation is described as a practical tooling convention
  rather than part of the core language definition
