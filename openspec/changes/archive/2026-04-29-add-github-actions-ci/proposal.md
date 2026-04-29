## Why

The repository currently lacks an automated validation path for pull requests
and branch pushes, which makes regressions easier to merge and forces
contributors to remember the right local test steps manually. Adding GitHub
Actions CI gives the project a repeatable, repository-native way to verify the
Python package on every change.

## What Changes

- Add a GitHub Actions workflow that runs the Python library test suite on
  pushes and pull requests.
- Define the baseline validation steps the CI workflow must perform, including
  dependency installation and automated test execution for the supported Python
  package.
- Cover a small version matrix so the project verifies compatibility across the
  supported Python runtime range instead of relying on a single interpreter.
- Document CI expectations so contributors know which repository checks must
  pass before merging changes.

## Capabilities

### New Capabilities

- `continuous-integration`: provide repository-hosted GitHub Actions
  validation for the Python package on pull requests and branch pushes.

### Modified Capabilities

- None.

## Impact

- GitHub Actions workflow configuration under `.github/workflows/`
- Python package validation commands and dependency bootstrap steps for
  `libs/py-myml`
- contributor expectations around required automated checks before merge
