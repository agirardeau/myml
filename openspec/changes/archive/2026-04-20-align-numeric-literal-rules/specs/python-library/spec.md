# Spec Delta: Python Library

## MODIFIED Requirements

### Requirement: Default mode conforms to the Myml language definition

In `default` mode, the library MUST accept exactly the Myml language described
in `docs/lang.md` and MUST reject unsupported YAML features, invalid scalar
forms, unsupported numeric separators, and non-normalized scientific notation.

#### Scenario: Parser matches corpus expectations

- **WHEN** a caller parses an input from the checked-in valid or invalid
  conformance corpus in the applicable mode
- **THEN** the parser result or raised error matches the expectations recorded
  for that corpus case
- **AND** corpus cases act as normative parser acceptance data for the library

#### Scenario: Supported Myml input is accepted

- **WHEN** a caller parses a document that is valid under `docs/lang.md`
- **THEN** the library returns the corresponding Python representation graph
- **AND** scalar resolution follows the order defined by the Myml language
  definition

#### Scenario: Plain fractional decimal with one leading zero is accepted

- **WHEN** a caller parses a plain decimal whose fractional form begins with
  exactly `0.`, such as `0.5`
- **THEN** the library accepts that value as a number
- **AND** additional leading zeroes remain disallowed

#### Scenario: Normalized scientific notation is accepted

- **WHEN** a caller parses scientific notation whose coefficient `m` satisfies
  `1 <= m < 10`, such as `1e6` or `1.5e2`
- **THEN** the library accepts that value as a number
- **AND** the parsed numeric value matches the represented magnitude

#### Scenario: Non-normalized scientific notation is rejected

- **WHEN** a caller parses scientific notation whose coefficient falls outside
  `1 <= m < 10`, such as `0.5e2` or `10e2`
- **THEN** the library raises an error
- **AND** the error identifies the scientific notation as invalid

#### Scenario: Unsupported numeric separators are rejected

- **WHEN** a caller parses a numeric token containing underscore separators
- **THEN** the library raises an error
- **AND** the error identifies the numeric token as invalid

#### Scenario: Unsupported YAML input is rejected

- **WHEN** a caller parses input that uses a YAML construct outside the Myml
  language definition
- **THEN** the library raises an error
- **AND** the error identifies the unsupported construct or malformed syntax as
  the cause
