# Design: Refactor Corpus

## Context

The current corpus contract splits cases into `corpus/cases/valid/` and
`corpus/cases/invalid/` and uses separate files such as `expected_parse.json`
and `error.json` to distinguish success and failure outcomes. That structure
worked when each case represented one parse outcome plus a small set of emit
fixtures, but it now fights the shape of the language contract.

One input can succeed in multiple modes, fail in other modes, and produce
different emitted output under different serializer settings. The current model
either duplicates the same input across valid and invalid trees or forces
mode-sensitive behavior into side conventions such as `modes`,
`emit_profiles`, and `roundtrip_edits` that no longer describe the full
contract clearly.

The refactor should produce a per-input manifest model that keeps one canonical
semantic graph for successful parses, expresses parse rejection inline where
needed, and supports multiple emit expectations with room for future emit
settings beyond `roundtrip`.

## Goals / Non-Goals

**Goals:**

* Represent each corpus input as a single stable case directory under
  `corpus/cases/<case-id>/`.
* Replace the current top-level `modes`, `emit_profiles`, and
  `roundtrip_edits` conventions with explicit parse and emit profile maps in
  `meta.json`.
* Keep one shared `expected_node_graph.json` artifact for successful parse
  outcomes within a case.
* Allow parse and emit failures to be declared inline in `meta.json` through
  structured `expect_error` objects.
* Require parse coverage for every supported mode while allowing profile
  compression through `modes: "all"` or explicit mode lists.
* Allow emit profiles to declare optional feature requirements through
  `requires`.
* Preserve a baseline contract by requiring each case to include at least one
  parse profile and one emit profile with no `requires`.
* Keep YAML only for the Myml syntax under test and emitted-output fixtures.

**Non-Goals:**

* Changing the Myml language definition in `docs/lang.md`.
* Defining every future emit option beyond establishing where such options live
  in the schema.
* Requiring every implementation to support optional features such as
  roundtrip emission.
* Introducing a checked-in aggregate corpus index.

## Decisions

### Use one case directory per input

Each corpus case will live directly at `corpus/cases/<case-id>/` with no
separate `valid/` or `invalid/` partition. The case directory remains the
stable identity, while parse and emit profiles inside `meta.json` describe the
expected behavior for that input.

This aligns the file layout with the actual problem shape: one input may have
multiple valid and invalid outcomes depending on mode and emit settings.

Alternatives considered:

* Keep `valid/` and `invalid/` and duplicate cases across both trees: rejected
  because it duplicates the same input and weakens the idea that a case is the
  authoritative home for one document.
* Keep a single parse outcome per case and model mode-specific failures as
  separate cases: rejected because it spreads one semantic example across
  multiple directories and makes corpus maintenance harder.

### Make `meta.json` the executable case manifest

`meta.json` will continue to be the authoritative per-case control file, but it
will now carry the executable profile model rather than only descriptive
metadata. It will contain:

* descriptive fields such as `summary`, `tags`, `spec_refs`, and `notes`
* `parse_profiles`, keyed by profile id
* `emit_profiles`, keyed by profile id

Each parse profile declares `modes` and exactly one of:

* `expect_node_graph`
* `expect_error`

Each emit profile declares:

* `mode`
* optional `options`
* optional `requires`
* exactly one of `expect_output` or `expect_error`

Both parse and emit profiles may declare `requires` when a profile depends on
optional implementation features, though the immediate use case is primarily on
the emit side.

Alternatives considered:

* Keep profile definitions as arrays with explicit `id` fields: rejected
  because keyed maps are easier to diff, reference, and validate.
* Keep error expectations in separate `error.json` files: rejected because
  inline structured errors are smaller, easier to trace, and avoid extra
  sidecar files for tiny payloads.

### Keep one canonical node-graph artifact per case

Successful parse profiles in a case will all reference the same
`expected_node_graph.json` artifact. This encodes the invariant that successful
parse modes for a given case produce the same semantic node graph.

This keeps the semantic center of the case explicit and prevents the corpus
from drifting into multiple near-duplicate parse artifacts for one input.

Alternatives considered:

* One node-graph file per parse profile: rejected because it duplicates the
  same semantic expectation and weakens the cross-mode equivalence invariant.
* Inline node-graph JSON inside `meta.json`: rejected because the graph can be
  larger than metadata and is easier to diff as a dedicated file.

### Use `modes` on parse profiles and allow the scalar value `"all"`

Parse profiles will declare applicability through a required `modes` field.
That field may be either:

* an array of explicit mode names
* the scalar string `"all"`

Using `"all"` as a scalar avoids ambiguous combinations such as
`["all", "default"]`.

The profile set for a case must cover every supported parse mode exactly once.
If one parse profile uses `"all"`, it is the only parse profile for that case.

Alternatives considered:

* Single `mode` per parse profile: rejected because it creates repetitive
  profiles when multiple modes share the same expectation.
* `["all"]` as an array sentinel: rejected because it invites confusing mixed
  lists and adds validation edge cases.

### Keep emit mode top-level and future emit knobs under `options`

Each emit profile will keep `mode` as a required top-level field because it is
the primary selector for emitted behavior. Any additional emit parameters, such
as `roundtrip`, will live under an `options` object.

This keeps the common case compact while giving the schema room to grow as
additional emit settings appear.

Alternatives considered:

* Flatten every emit setting to the profile top level: rejected because the
  shape becomes noisy once more emit parameters are added.
* Put `mode` inside `options`: rejected because `mode` is mandatory and should
  stay visually prominent.

### Make optional feature gating explicit through `requires`

Parse and emit profiles may declare a `requires` array naming optional
implementation features needed for that profile to be relevant, such as
`roundtrip`.

This gives harnesses a machine-readable way to skip unsupported optional
profiles without guessing from emit options alone.

Alternatives considered:

* Infer capability gating entirely from `options`: rejected because settings
  such as `roundtrip` describe behavior, while `requires` describes whether a
  harness should treat the profile as applicable.
* Keep capability gating only on emit profiles: rejected because the corpus now
  also wants a meaningful invariant that each case provides a baseline parse
  profile with no `requires`, and future optional parse capabilities should not
  require another schema redesign.

### Require a baseline parse and emit path with no `requires`

Each case must include at least one parse profile with no `requires` and at
least one emit profile with no `requires`. This preserves a baseline contract
that remains relevant even for implementations that do not support optional
features such as roundtrip emission.

Alternatives considered:

* Require only a non-roundtrip emit profile: rejected because `requires`
  expresses the more general invariant as optional features grow.
* Allow cases that only define optional profiles: rejected because that would
  make some corpus entries unusable for baseline implementations.

## Risks / Trade-offs

* More expressive `meta.json` files can become harder to author by hand ->
  Mitigate by documenting the schema clearly in `corpus/README.md` and keeping
  the invariant set small and regular.
* `"all"` can accidentally widen the meaning of a case when new modes are
  added later -> Mitigate by documenting that `"all"` means all currently
  supported parse modes and by recommending explicit mode lists when intent is
  narrower.
* Inline error expectations make `meta.json` larger -> Mitigate by keeping
  error objects structured and compact and by moving only emitted/output text
  into dedicated fixture files.
* Existing harnesses and contributors already assume `valid/` and `invalid/`
  trees -> Mitigate by updating documentation and the Python harness in the same
  change.

## Migration Plan

1. Update the corpus specification and contributor documentation to describe the
   new single-case layout and profile schema.
2. Move existing cases from `corpus/cases/valid/` and `corpus/cases/invalid/`
   into `corpus/cases/<case-id>/`.
3. Rename each `expected_parse.json` file to `expected_node_graph.json`.
4. Fold existing `error.json` payloads into the appropriate parse profiles as
   `expect_error`.
5. Convert existing `modes`, `emit_profiles`, and `roundtrip_edits` metadata
   into explicit `parse_profiles` and `emit_profiles`.
6. Update the Python harness and any related docs to read the new manifest
   format.
7. Validate that every case covers all supported parse modes exactly once and
   includes baseline parse and emit profiles with no `requires`.

## Open Questions

* Should the corpus documentation recommend canonical profile ids such as
  `default`, `strict`, `y11safety`, and `roundtrip`, or only define the schema
  and leave ids fully contributor-chosen?
* Should future parse-specific optional features also gain `requires`, or is
  it better to keep parse coverage strictly mode-complete unless a concrete
  need appears?
