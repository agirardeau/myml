# Spec: Continuous Integration

## Requirements

### Requirement: Repository provides GitHub Actions CI validation

- Automated validation runs using Github Actions
- Automated validation runs on pull requests and push events

### Requirement: CI validates the Python library

- The CI workflow runs the checked-in automated test suite for `libs/py-yaml`
- The CI workflow uses commands that contributors can reproduce locally
- The CI version matrix includes the package's declared minimum supported Python
  version and the two most recent stable python versions

