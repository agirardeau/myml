## 1. Workflow Setup

- [x] 1.1 Create a GitHub Actions workflow under `.github/workflows/` for CI on `push` and `pull_request`
- [x] 1.2 Configure the workflow to set up a Python version matrix that includes the minimum supported version from `libs/py-myml/pyproject.toml` and at least one newer version

## 2. Package Validation

- [x] 2.1 Add CI steps to install `libs/py-myml` and any required test tooling with standard Python packaging commands
- [x] 2.2 Add CI steps to run the repository's existing Python test suite for `libs/py-myml` and fail the job on any test failure

## 3. Verification and Documentation

- [x] 3.1 Confirm the workflow commands are reproducible locally and match the repository's current layout and test entry points
- [x] 3.2 Update repository documentation as needed so contributors know the baseline CI checks and where they run
