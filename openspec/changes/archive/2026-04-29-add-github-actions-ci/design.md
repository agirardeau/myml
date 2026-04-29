## Context

`myml` currently ships as a Python package under `libs/py-myml`, and the
repository already includes a checked-in unit test suite plus a conformance
corpus. Contributors can run those checks locally, but the repository has no
first-party automation that runs them on GitHub for pull requests or branch
pushes.

This is a cross-cutting repository change because the workflow has to connect
GitHub event triggers, Python setup, package installation, and the existing
test commands in a way that is stable for contributors and easy to extend
later.

## Goals / Non-Goals

**Goals:**

- Add a repository-owned GitHub Actions workflow for automated validation.
- Run the existing Python package test suite from `libs/py-myml` on pull
  requests and pushes.
- Verify the package against more than one supported Python runtime so obvious
  compatibility regressions are caught early.
- Keep the workflow simple enough that contributors can reproduce it locally.

**Non-Goals:**

- Introducing a separate lint, type-check, release, or publish pipeline in the
  same change.
- Reorganizing the repository into a monorepo build system.
- Enforcing branch-protection settings that must be configured in GitHub
  repository settings rather than in-versioned files.

## Decisions

### Use a single workflow dedicated to CI validation

The repository will add one workflow file under `.github/workflows/` that owns
the baseline validation path. The workflow will trigger on `push` and
`pull_request`, which covers day-to-day contributor flows without adding
release-specific behavior yet.

Alternatives considered:

- Split PR and push validation into multiple workflows: rejected because the
  repository currently has only one package and one baseline check set.
- Trigger only on pull requests: rejected because direct branch pushes should
  also get automated feedback.

### Scope execution to `libs/py-myml` and use the package's native test command

The workflow will install the Python package from `libs/py-myml` and run the
existing `unittest`-based suite from that package directory. This matches the
current repository layout and avoids inventing a separate root-level test
runner before the project needs one.

Alternatives considered:

- Add a new root task runner just for CI: rejected because it adds ceremony
  without reducing complexity in the current repo shape.
- Switch the test suite to another framework as part of CI setup: rejected
  because CI should automate the current validation path first.

### Use a small supported-version matrix starting at the declared minimum

The workflow will test at least the declared minimum supported version from
`libs/py-myml/pyproject.toml` and one newer CPython version. That keeps the
matrix fast while still checking both the lower compatibility floor and a
newer runtime that contributors are likely to use.

Alternatives considered:

- Test only one Python version: rejected because it would not validate the
  support range implied by `requires-python = \">=3.11\"`.
- Test every available CPython version on every push: rejected because the
  added runtime cost is unnecessary for an initial CI baseline.

### Keep dependency bootstrap explicit and reproducible

The workflow will use `actions/setup-python`, upgrade `pip`, and install the
package with its test dependencies through standard Python packaging commands.
The CI steps should map directly to commands contributors can run locally,
which keeps failure diagnosis straightforward.

Alternatives considered:

- Use a custom composite action immediately: rejected because the workflow is
  small enough that inline steps are easier to read and maintain.
- Rely on prebuilt cached environments without explicit install steps:
  rejected because clarity matters more than optimization for the first pass.

## Risks / Trade-offs

- Matrix runs increase total CI time -> Keep the initial matrix small and
  aligned with the package's supported range.
- Workflow behavior can drift from local contributor habits -> Use ordinary
  Python install and test commands that can be copied locally.
- The repo may later need linting or packaging checks in addition to tests ->
  Start with a clearly named baseline workflow that can be extended without
  replacing it.

## Migration Plan

1. Add the workflow file under `.github/workflows/`.
2. Document the CI commands or expectations in repository docs if needed.
3. Open a pull request so the workflow executes in GitHub and confirm the
   first run matches local expectations.
4. If CI proves too narrow or too slow, adjust the version matrix or split
   future checks into separate workflows.

Rollback is straightforward: revert the workflow file if it causes operational
issues or blocks development unexpectedly.

## Open Questions

- Which newer Python version should be the second matrix target for this repo:
  3.12 only, or 3.12 plus 3.13?
- Should the first CI pass include a dedicated packaging build check in
  addition to the unit test suite?
