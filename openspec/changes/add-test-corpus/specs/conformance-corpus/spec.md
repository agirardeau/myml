# Spec Delta: Conformance Corpus

## ADDED Requirements

### Requirement: Canonical Conformance Corpus

The repository contains a canonical conformance corpus for Myml.

#### Scenario: Valid case is represented canonically

- **WHEN** a test case represents valid Myml input
- **THEN** the corpus stores the input document together with a machine-readable
  expected result
- **AND** the case includes metadata describing the rule areas it covers

#### Scenario: Invalid case is represented canonically

- **WHEN** a test case represents invalid Myml input
- **THEN** the corpus stores the input document together with a machine-readable
  expected error description
- **AND** the case includes metadata describing the rule areas it covers

### Requirement: Coverage Matrix Tracks Language Rules

The repository contains a coverage matrix that maps language rules to corpus
cases.

#### Scenario: Rule coverage is discoverable

- **WHEN** a contributor reviews corpus coverage
- **THEN** they can determine which corpus cases cover a given rule or mode
- **AND** uncovered rule areas are visible without inspecting every case

### Requirement: Corpus Layout Supports Growth

The corpus layout supports incremental growth without changing existing case
identifiers or rewriting earlier fixtures.

#### Scenario: New case is added

- **WHEN** a contributor adds a new corpus case
- **THEN** the case can be added in its own stable directory with metadata and
  expected output artifacts
- **AND** the coverage matrix can reference the new case without restructuring
  existing cases

### Requirement: Corpus Documentation Recommends a Practical Extension

The repository documents a recommended filename extension for Myml source files.

#### Scenario: Contributor chooses a filename for Myml input

- **WHEN** a contributor creates a corpus input file or example Myml document
- **THEN** the repository documentation recommends the `.yaml` extension
- **AND** the recommendation is described as a practical tooling convention
  rather than part of the core language definition
