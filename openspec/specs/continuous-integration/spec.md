# continuous-integration Specification

## Purpose
TBD - created by archiving change add-github-actions-ci. Update Purpose after archive.
## Requirements
### Requirement: Repository provides GitHub Actions CI validation

The repository MUST include a GitHub Actions workflow that runs automated
validation for the Python package on pull requests and push events.

#### Scenario: Pull request triggers validation

- **WHEN** a contributor opens or updates a pull request against the repository
- **THEN** GitHub Actions runs the repository CI workflow
- **AND** the workflow executes the configured Python package validation steps

#### Scenario: Push triggers validation

- **WHEN** a contributor pushes commits to a branch in the repository
- **THEN** GitHub Actions runs the repository CI workflow for that push
- **AND** the workflow reports whether validation passed or failed

### Requirement: CI validates the Python package with repository-native commands

The CI workflow MUST set up Python, install the package from `libs/py-myml`,
and run the repository's checked-in automated test suite using commands that
contributors can reproduce locally.

#### Scenario: Workflow prepares the package environment

- **WHEN** the CI job starts on a GitHub-hosted runner
- **THEN** it installs a supported Python runtime
- **AND** it installs the package from `libs/py-myml`
- **AND** it bootstraps any dependencies required to execute the test suite

#### Scenario: Workflow runs automated verification

- **WHEN** the package environment is prepared
- **THEN** the workflow runs the Python package's automated tests
- **AND** a failing test causes the CI job to fail
- **AND** a fully passing test run causes the CI job to succeed

### Requirement: CI covers the supported runtime floor and a newer runtime

The CI workflow MUST validate the Python package on a version matrix that
includes the package's declared minimum supported Python version and at least
one newer supported CPython version.

#### Scenario: Matrix includes compatibility floor

- **WHEN** the CI workflow defines its Python-version matrix
- **THEN** that matrix includes the minimum version declared by
  `libs/py-myml/pyproject.toml`

#### Scenario: Matrix includes more than one supported version

- **WHEN** the CI workflow runs for a change
- **THEN** it executes validation on at least two supported Python versions
- **AND** at least one version in that set is newer than the declared minimum

