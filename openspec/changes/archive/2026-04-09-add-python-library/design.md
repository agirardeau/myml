# Design: Add Python Library

## Context

The repository currently contains the Myml language definition in
`docs/lang.md` and a conformance corpus, but no reference implementation. This
change introduces the first Python package for parsing and emitting Myml. The
implementation will live in `libs/py-myml`, leaving room for future
language-specific libraries to live alongside it under `libs/`.

The library needs to satisfy two different usage patterns:

* a simple value-oriented API for callers who want plain Python data structures
* an opt-in roundtrip mode for callers who need comments, whitespace, scalar
  style, and ordering preserved across load/edit/dump cycles

The public API should feel familiar to Python users coming from `PyYAML` and
`ruamel.yaml`, while remaining explicitly grounded in Myml rather than general
YAML. The language definition already establishes three behavioral modes:
default behavior, strict mode, and YAML 1.1 safety behavior. The public Python
API will expose the last mode as `y11safety`, so the design needs to connect
that public mode name back to the language rules in `docs/lang.md`.

`prompts/python.md` is treated as background only and will be removed so the
OpenSpec artifacts become the canonical requirements source.

## Goals / Non-Goals

**Goals:**

* Provide `load`, `loads`, `dump`, and `dumps` entry points for Myml documents.
* Place the Python implementation in `libs/py-myml` using a layout that can
  coexist cleanly with future libraries in other languages.
* Keep the baseline runtime install free of required external runtime
  dependencies.
* Keep default-mode parse and emit behavior aligned with `docs/lang.md`.
* Support an explicit `mode` option with `default`, `strict`, and `y11safety`
  values.
* Support an explicit `roundtrip` option that preserves formatting data when
  requested.
* Make unchanged roundtrip documents dump back to their original text.
* Preserve surrounding comments, whitespace, scalar style, and key order as far
  as possible when callers edit roundtrip data.
* Validate parser and emitter behavior against the checked-in corpus as the
  primary acceptance source for the library.

**Non-Goals:**

* Supporting YAML features outside the Myml language definition.
* Providing full API parity with either `PyYAML` or `ruamel.yaml`.
* Defining every future extension point for custom schema, tags, or anchors.
* Optimizing roundtrip mode for the same performance profile as plain parsing.

## Decisions

### Use a PyYAML-style functional API with explicit options

The initial public API will expose module-level `load`, `loads`, `dump`, and
`dumps` functions. Each function accepts keyword options for `mode` and
`roundtrip`.

This keeps the first release immediately familiar to `PyYAML` users and simple
for casual use. It also leaves room to add a richer configurable facade later
if repeated option reuse becomes important.

Alternatives considered:

* A `ruamel.yaml`-style stateful `YAML` object only: rejected because it adds
  ceremony for the most common use cases.
* Separate entry points per mode: rejected because it makes the public API
  harder to discover and extend.

### Place the implementation in `libs/py-myml`

The Python library will live in `libs/py-myml` rather than at the repository
root. This keeps implementation code clearly separate from the language spec,
the corpus, and OpenSpec artifacts, while also giving the repository a natural
place to add future implementations such as `libs/js-myml` or `libs/rs-myml`.

Alternatives considered:

* Root-level Python package: rejected because it makes the repository layout
  less clear as more non-Python assets accumulate.
* Language-specific top-level folders without a shared parent: rejected because
  `libs/` gives a simpler convention for multi-language growth.

### Require no runtime dependencies for the baseline install

The default Python package install will have no required external runtime
dependencies. Users must be able to install and use the baseline library
without separately installing parser backends or native extensions.

This preserves the simple-install experience while still allowing future
optional extras such as `speedups` or similar opt-in accelerators.

Alternatives considered:

* Require a YAML library dependency from day one: rejected because it weakens
  the low-friction installation goal.
* Forbid all optional dependencies forever: rejected because it would block
  future opt-in performance improvements without helping the default install.

### Separate semantic values from formatting-preserving values

The parser will build an internal syntax tree that retains tokens, comments,
spacing, scalar style, and source ordering. From that tree, the library can
produce either:

* plain Python containers and scalars when `roundtrip=False`
* roundtrip-aware wrapper objects when `roundtrip=True`

This lets one parser serve both value-oriented and format-preserving workflows
without losing fidelity for the roundtrip path.

Alternatives considered:

* Preserving formatting metadata on plain `dict` and `list` objects: rejected
  because builtins do not offer a stable place for that metadata.
* Returning `ruamel.yaml` object types directly: rejected because it would leak
  an external object model into the Myml API and make Myml-specific behavior
  harder to specify.

### Treat roundtrip preservation as a dump concern backed by change tracking

Roundtrip-aware values will retain enough metadata to reproduce the original
document when untouched and to preserve unaffected formatting when edited. The
emitter will re-use preserved trivia for unchanged nodes and re-render only the
nodes that became dirty.

This is the most practical way to support exact identity for no-op roundtrips
without forcing every edited document to fall back to a fully normalized
serialization.

Alternatives considered:

* Always re-serialize from semantic values: rejected because it would lose
  comments and whitespace immediately.
* Preserve only comments but not other formatting: rejected because the request
  explicitly calls out whitespace and formatting, not just comments.

### Make mode selection string-based and consistent across parse and emit

The library will use `mode="default"`, `mode="strict"`, or
`mode="y11safety"` instead of separate booleans. Parsing and emitting will both
honor the selected mode.

This avoids contradictory combinations such as multiple boolean flags being set
at once. It also creates a clean place to add future mode variants without
expanding the function signature unpredictably.

Alternatives considered:

* Boolean flags such as `strict=True` and `yaml_1p1_safety=True`: rejected
  because they allow invalid combinations and do not communicate precedence.
* Parser-only mode handling: rejected because emit behavior also changes, such
  as forced quoting in strict and compatibility modes.

### Implement Myml behavior directly rather than wrapping a general YAML parser

The implementation may borrow ideas from `PyYAML` and `ruamel.yaml`, but the
library will not treat either as the authoritative parser or emitter backend.
Myml has narrower syntax, different rejection rules, and stricter roundtrip
requirements than general-purpose YAML libraries provide out of the box.

Alternatives considered:

* Thin wrapper over `PyYAML`: rejected because it does not preserve formatting
  and accepts YAML constructs outside Myml.
* Thin wrapper over `ruamel.yaml`: rejected because it still targets broader
  YAML behavior and would leave Myml-specific validation and mode semantics
  underspecified.

### Extend the corpus so it can drive emission verification too

The current corpus model stores one parse expectation and one emit expectation
per valid case. That is enough for parser conformance, but it is too narrow for
the Python library because the same semantic value may have different expected
emitted text in `default`, `strict`, `y11safety`, and `roundtrip` settings.

To keep verification corpus-driven instead of introducing Python-only approval
fixtures, valid cases should support multiple named emitted-output fixtures,
with one `expected_emit_{PROFILE}.yaml` file per setting profile and
`meta.json` recording the profile-to-file mapping. A harness can then run the
same case through multiple settings and compare the output to the appropriate
fixture file.

Mode-sensitive parse failures do not require a schema change. Those can remain
separate corpus cases because the same input being valid in one mode and
invalid in another is still clearly representable with distinct valid and
invalid cases.

This keeps the public API, the implementation, and the acceptance criteria
aligned from the start without inventing a second test fixture format.

### Add Python packaging and a corpus-driven harness in the same change

The change will introduce a standard Python package layout and a test harness
that exercises parse and emit behavior directly against the conformance corpus.

This keeps the implementation aligned with the repo-owned acceptance data.

## Risks / Trade-offs

* Exact preservation after structural edits is complex -> Mitigate by defining
  unchanged-document identity as the hard requirement and using dirty-node
  tracking for incremental re-rendering.
* Roundtrip wrappers add cognitive overhead -> Mitigate by keeping them opt-in
  and leaving the default API value-oriented.
* `y11safety` is a public name, while `docs/lang.md` uses YAML 1.1 Safety Mode
  -> Mitigate by documenting the mapping clearly in code and tests.
* No required runtime dependencies may reduce peak performance in the baseline
  implementation -> Mitigate by optimizing the pure-Python path first and
  leaving room for optional accelerators later.
* Roundtrip mode will be slower and more memory-intensive -> Mitigate by
  keeping default mode lean and by benchmarking only the default path as the
  general-use baseline.
* Corpus coverage may not yet capture all formatting-preservation edge cases ->
  Mitigate by extending the corpus to include mode-aware emit fixture files and
  roundtrip-preservation cases before treating the harness as complete.

## Migration Plan

This change has no runtime migration for existing users because no Python
library exists yet. Implementation should proceed in this order:

1. Add Python packaging, module layout, and public API scaffolding.
   The package root lives in `libs/py-myml`.
2. Implement default-mode parsing and emitting against `docs/lang.md`.
3. Extend the corpus contract and fixtures where needed so emit verification can
   stay corpus-driven.
4. Add roundtrip-aware value types and preservation metadata.
5. Implement `strict` and `y11safety` mode behavior for parse and emit.
6. Validate against the corpus through the Python harness.
7. Remove `prompts/python.md` so proposal, design, specs, and code are the
   only maintained sources of truth.

## Open Questions

* Should the first implementation expose a public class for roundtrip-aware
  values, or should those types remain documented but not emphasized in the top
  level namespace?
* Should dump helpers default to preserving trailing newline behavior in
  roundtrip mode, or only preserve it when the loaded document originally had
  one?
* Does the project want the first release to include file-object helpers only
  through `load` and `dump`, or also convenience wrappers for filesystem paths?
