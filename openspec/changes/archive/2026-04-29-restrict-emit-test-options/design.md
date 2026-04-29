## Context

The corpus schema and documentation currently describe emit profiles as if they
can carry arbitrary `options`, but the checked-in harness only treats
`roundtrip` as a supported optional feature. One corpus case,
`comments-and-empty-lines`, also includes `roundtrip_edit_note`, which uses an
embedded edit script in `options.edits` before emission. That makes the corpus
contract broader than the stable behavior the harness is intended to validate.

This change narrows the contract so the corpus continues to cover:

- baseline emission for each supported mode
- roundtrip-preserving re-emission when the implementation supports
  `roundtrip`

It intentionally leaves format-aware edit behavior to targeted library tests
rather than corpus metadata.

## Goals / Non-Goals

**Goals:**

- Make the conformance-corpus emit-profile contract explicit and narrow.
- Align corpus documentation, corpus fixtures, and the Python harness around
  `roundtrip` as the only supported non-baseline emit-test option.
- Remove the one checked-in emit profile that scripts edits through corpus
  metadata.

**Non-Goals:**

- Remove or weaken the library's format-aware editing API.
- Remove unit tests that directly verify edit-preserving emission behavior.
- Redesign parse profiles or general corpus layout.

## Decisions

Define emit-profile options as roundtrip-only.
Rationale: the current harness already has a single optional emit capability,
and making that explicit prevents future corpus drift where new option shapes
appear without a deliberate spec change.

Reject scripted edits in corpus metadata.
Rationale: edit scripting mixes mutation semantics into a corpus intended to be
the canonical oracle for parse and emit acceptance. That style of behavior is
better covered by focused library tests that can express edits directly in
code.

Make the harness fail on unsupported emit options.
Rationale: silently accepting unknown option keys would recreate the same
ambiguity. A hard failure keeps the contract honest and forces future
extensions to update the spec first.

## Risks / Trade-offs

[Less corpus coverage for mutation-driven emission] -> Keep edit behavior
covered in targeted library tests and reserve corpus fixtures for baseline and
roundtrip acceptance.

[Future emit-test options need a spec change before landing] -> Accept this as
intentional friction so new corpus capabilities stay explicit and reviewable.
