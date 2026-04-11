# Spec Delta: Conformance Corpus

## MODIFIED Requirements

### Requirement: Canonical Conformance Corpus

The repository MUST contain a canonical conformance corpus for Myml.

#### Scenario: Valid case is represented canonically

- **WHEN** a test case represents valid Myml input
- **THEN** the corpus stores the input document together with a machine-readable
  parse expectation
- **AND** the corpus stores one or more emitted-output fixture files named
  `expected_emit_{PROFILE}.yaml`
- **AND** `meta.json` identifies which emitted-output fixture file applies to
  each supported library setting profile
- **AND** the case includes metadata describing the rule areas it covers

#### Scenario: Invalid case is represented canonically

- **WHEN** a test case represents invalid Myml input
- **THEN** the corpus stores the input document together with a machine-readable
  expected error description
- **AND** the case includes metadata describing the rule areas it covers

### Requirement: JSON Control Files Separate the Oracle from the Syntax Under Test

Corpus control files MUST use JSON rather than YAML.

#### Scenario: Harness reads expected parse or error data

- **WHEN** a test harness reads corpus metadata or expectations
- **THEN** it reads JSON control files rather than YAML control files
- **AND** the Myml input under test remains isolated in `input.yaml`

#### Scenario: Harness reads multiple emit expectations

- **WHEN** a test harness reads emit expectations for a valid case
- **THEN** it can discover the emitted-output fixture file for each supported
  setting profile from `meta.json`
- **AND** it reads the expected emitted Myml text from those
  `expected_emit_{PROFILE}.yaml` files
- **AND** it does not need a language-specific sidecar expectation format
