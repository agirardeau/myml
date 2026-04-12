# Spec: Conformance Corpus

## Requirements

### Requirement: Canonical Conformance Corpus

The repository MUST contain a canonical conformance corpus for Myml.

#### Scenario: Case is represented canonically

- **WHEN** a test case represents one Myml input document
- **THEN** the corpus stores that case under `corpus/cases/<case-id>/`
- **AND** the case stores the Myml input under test in `input.yaml`
- **AND** successful parse outcomes for the case reference a canonical
  `expected_node_graph.json` artifact
- **AND** successful emit outcomes for the case reference one or more
  `expected_emit_{PROFILE}.yaml` files
- **AND** the case includes `meta.json` describing parse and emit profiles

### Requirement: Per-Case Metadata Is Authoritative

Per-case `meta.json` files MUST be the authoritative source of corpus metadata
and profile expectations.

#### Scenario: Tooling needs a case catalog

- **WHEN** tooling needs to discover corpus cases or their covered rules
- **THEN** it derives that information from the per-case `meta.json` files
- **AND** no separate checked-in aggregate metadata file is required for
  correctness

#### Scenario: Tooling discovers parse and emit profiles

- **WHEN** tooling reads a case `meta.json`
- **THEN** it finds `parse_profiles` and `emit_profiles` keyed by profile id
- **AND** each parse profile declares `modes`
- **AND** each emit profile declares `mode`
- **AND** either kind of profile may declare `requires`
- **AND** descriptive case metadata remains in the same `meta.json` file

### Requirement: JSON Control Files Separate the Oracle from the Syntax Under Test

Corpus control files MUST use JSON rather than YAML.

#### Scenario: Harness reads expected parse or error data

- **WHEN** a test harness reads corpus metadata or expectations
- **THEN** it reads JSON control files rather than YAML control files
- **AND** the Myml input under test remains isolated in `input.yaml`

#### Scenario: Harness reads emit expectations

- **WHEN** a test harness reads emit expectations for a case
- **THEN** it discovers emit profile metadata from `meta.json`
- **AND** it reads expected emitted Myml text from the referenced
  `expected_emit_{PROFILE}.yaml` files
- **AND** parse and emit failures are represented as structured JSON data in
  `meta.json`

### Requirement: Corpus Layout Supports Growth

The corpus layout MUST support incremental growth without changing existing
case identifiers or rewriting earlier fixtures.

#### Scenario: New case is added

- **WHEN** a contributor adds a new corpus case
- **THEN** the case can be added in its own stable directory with metadata and
  expected output artifacts
- **AND** repo-level coverage notes can be updated without restructuring
  existing cases

### Requirement: Parse Profiles Cover Supported Modes

Each case MUST define parse expectations that cover every supported parse mode
exactly once.

#### Scenario: Parse profiles enumerate supported modes

- **WHEN** a contributor defines parse profiles for a case
- **THEN** each parse profile declares `modes` as either an explicit array of
  supported mode names or the scalar value `"all"`
- **AND** the set of parse profiles covers every supported parse mode for the
  corpus exactly once
- **AND** if one parse profile uses `"all"`, no other parse profile is present

#### Scenario: Parse profile succeeds

- **WHEN** a parse profile expects a successful parse outcome
- **THEN** that profile declares `expect_node_graph`
- **AND** it references the case's canonical `expected_node_graph.json`
- **AND** it does not declare `expect_error`

#### Scenario: Parse profile fails

- **WHEN** a parse profile expects a rejected parse outcome
- **THEN** that profile declares `expect_error`
- **AND** the error expectation is stored inline in `meta.json`
- **AND** it does not declare `expect_node_graph`

### Requirement: Emit Profiles Express Serialization Expectations

Each case MUST define zero or more named emit profiles describing serializer
behavior for the case's semantic graph.

#### Scenario: Emit profile succeeds

- **WHEN** an emit profile expects successful serialization
- **THEN** the profile declares a top-level `mode`
- **AND** it may declare additional emit parameters under `options`
- **AND** it declares `expect_output` referencing an
  `expected_emit_{PROFILE}.yaml` file
- **AND** it does not declare `expect_error`

#### Scenario: Emit profile fails

- **WHEN** an emit profile expects serialization to fail
- **THEN** the profile declares a top-level `mode`
- **AND** it may declare additional emit parameters under `options`
- **AND** it declares `expect_error` inline in `meta.json`
- **AND** it does not declare `expect_output`

### Requirement: Optional Feature Gating Is Explicit

The corpus MUST support optional feature requirements on parse and emit
profiles through a `requires` array.

#### Scenario: Harness checks profile applicability

- **WHEN** a parse or emit profile depends on optional implementation features
- **THEN** the profile declares those features in `requires`
- **AND** a harness can use `requires` to decide whether the profile is
  relevant

#### Scenario: Case provides a baseline path

- **WHEN** a contributor authors a corpus case
- **THEN** the case includes at least one parse profile with no `requires`
- **AND** the case includes at least one emit profile with no `requires`
