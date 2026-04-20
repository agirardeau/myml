# Spec Delta: Conformance Corpus

## ADDED Requirements

### Requirement: Numeric lexical boundary cases are explicit in the corpus

The conformance corpus MUST include focused cases that distinguish accepted
plain fractional decimals from rejected separator syntax and rejected
non-normalized scientific notation.

#### Scenario: Plain fractional decimal is covered as valid input

- **WHEN** a contributor adds or updates a corpus case for a plain fractional
  decimal such as `0.5`
- **THEN** the case includes a successful parse profile referencing the
  canonical `expected_node_graph.json`
- **AND** the case includes at least one successful emit profile for the same
  semantic value

#### Scenario: Underscore separator syntax is covered as invalid input

- **WHEN** a contributor adds or updates a corpus case containing an underscore
  separator in a numeric token, such as `1_000`
- **THEN** the case records a rejected parse outcome in `meta.json`
- **AND** the case does not declare a successful parse profile for that input

#### Scenario: Non-normalized scientific notation is covered as invalid input

- **WHEN** a contributor adds or updates a corpus case containing scientific
  notation whose coefficient is outside `1 <= m < 10`, such as `0.5e2` or
  `10e2`
- **THEN** the case records a rejected parse outcome in `meta.json`
- **AND** the corpus still includes a separate successful case for normalized
  scientific notation such as `1e6` or `1.5e2`
