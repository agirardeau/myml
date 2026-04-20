## Context

The Python library already has most of the internal pieces needed for
format-aware editing. Its syntax tree distinguishes node-local metadata such as
scalar style and container style from entry-local metadata such as pre-node
trivia and end-of-line comments, and mappings already preserve key order.

The public API does not expose that model cleanly. Roundtrip-loaded mappings
and sequences can be mutated with normal Python operations, but callers can
only inject plain values. That means a caller can preserve formatting parsed
from source text, but cannot intentionally create new formatting metadata such
as `|` versus `>`, a pre-node comment, an end-of-line comment, or a precise key
insertion point.

This change needs to turn the existing preservation-oriented internals into an
explicit editing API without losing the current ergonomic path:

- plain Python values remain the default for ordinary parsing
- `loads(..., roundtrip=True)` continues to opt callers into formatting-aware
  editing
- callers gain explicit constructors for durable formatting metadata and
  explicit operations for structural placement

## Goals / Non-Goals

**Goals:**

- Expose `scalar()`, `mapping()`, and `sequence()` as durable node-formatting
  constructors.
- Expose `entry()` as the durable representation for entry-local formatting.
- Expose mutation-time placement APIs such as `insert()`, `move_before()`,
  `move_after()`, and `reorder()` on format-aware mappings.
- Allow callers to upgrade plain mappings and sequences into format-aware
  wrappers through `as_format_aware()` instead of forcing a text roundtrip.
- Preserve backward compatibility for existing roundtrip workflows that rely on
  `loads(..., roundtrip=True)` and plain `mapping[key]` access.
- Ensure emission honors explicitly injected formatting metadata on edited or
  newly inserted values, not only formatting parsed from existing documents.

**Non-Goals:**

- Storing formatting metadata directly on builtin `dict` or `list` objects.
- Exposing the raw internal AST as the primary public editing surface.
- Supporting YAML formatting features outside the Myml language definition.
- Making placement semantics implicit in value constructors.

## Decisions

### Keep parsing opt-in as `roundtrip=True`, but document the runtime model as format-aware editing

The parse-time switch will remain `roundtrip=True` so current callers do not
need to relearn the entry point. The runtime editing model introduced by this
change will be documented as format-aware editing, because formatting metadata
may come from a roundtrip parse or from explicit constructors supplied by the
caller.

This preserves backward compatibility while giving the public API vocabulary
that matches the actual behavior after this change.

Alternatives considered:

- Rename the parse flag immediately: rejected because it would create avoidable
  churn for existing callers.
- Keep "roundtrip" as the only public concept: rejected because it suggests
  formatting can only come from parsed source text.

### Represent node-local formatting with explicit constructors

The library will expose:

- `scalar(value, *, style=...)`
- `mapping(value=None, *, style=...)`
- `sequence(value=None, *, style=...)`

These constructors represent durable node-local formatting choices such as
plain/single/double/literal/folded scalar style and block/flow container
style. They can be inserted into existing format-aware containers and survive
subsequent reordering or value replacement.

Node constructors intentionally do not carry comments or placement
instructions. Those belong to different layers of the model.

Alternatives considered:

- Reuse plain Python values plus many keyword arguments on every mutation:
  rejected because durable formatting state becomes awkward to reuse and reason
  about.
- Put entry comments directly on scalar constructors: rejected because comments
  belong to entries, not values, and the same value can appear in multiple
  entry contexts.

### Represent entry-local formatting with an explicit `entry()` wrapper

The library will expose `entry(value, *, before=None, eol_comment=None)` as the
durable wrapper for formatting attached to a mapping entry or sequence item.
This keeps entry-local concerns distinct from node-local concerns.

Format-aware containers will accept either plain values, node constructors, or
`entry()` values during assignment and insertion. Existing entries will be
editable through container-specific entry accessors so callers can inspect or
modify comments without changing `mapping[key]` semantics.

Alternatives considered:

- Store entry-local metadata on scalar constructors: rejected because it
  collapses two different concepts and makes reused values ambiguous.
- Require every edit to go through a low-level entry object API: rejected
  because it would make common updates heavier than necessary.

### Keep placement as an operation, not a property of inserted values

Placement intent is scoped to a single mutation, so it will live on methods
instead of constructors. Format-aware mappings will expose:

- `insert(key, value, *, before=None, after=None)`
- `move_before(key, anchor_key)`
- `move_after(key, anchor_key)`
- `reorder(keys)`

`reorder(keys)` will require a complete ordering of the mapping's keys so its
behavior is explicit and testable. `insert()` will reject calls that specify
both `before` and `after`.

Alternatives considered:

- Encode placement on constructors or `entry()` objects: rejected because the
  same object reused in another mapping would carry stale placement intent.
- Treat `__setitem__` as placement-aware: rejected because ordinary assignment
  should remain simple replace-or-append behavior.

### Add an explicit upgrade path for plain containers

The library will expose `as_format_aware(value, *, mode="default")` for plain
Python mappings and sequences. This returns the same family of wrappers used by
`loads(..., roundtrip=True)` so callers can build semantic data first and opt
into formatting-aware editing later.

The upgrade helper will apply only to mappings and sequences. Plain scalars do
not need a wrapper because explicit scalar formatting is already handled by
`scalar()`.

Alternatives considered:

- Require callers to re-emit and reparse text to become format-aware: rejected
  because it is wasteful and obscures intent.
- Auto-upgrade every parsed mapping and sequence: rejected because the default
  value-oriented API should stay lightweight.

### Preserve existing scalar access semantics and add explicit entry accessors

`mapping[key]` and sequence indexing will continue to return semantic values or
container wrappers, not scalar wrapper objects. This avoids breaking callers
that expect Python scalars from roundtrip-loaded mappings.

Entry metadata for existing content will be edited through explicit accessors
such as `mapping.entry(key)` and a sequence-item equivalent. That keeps the
common read path simple while still making comment and placement metadata
reachable.

Alternatives considered:

- Return scalar wrapper objects from all indexed access: rejected because it
  would be a breaking behavioral change and make ordinary reads noisier.
- Hide existing entry metadata from callers: rejected because the new API would
  otherwise help only with insertion, not modification.

### Make explicit formatting metadata authoritative for dirty nodes

When a caller replaces a value with `scalar(..., style="single")`,
`scalar(..., style="folded")`, `mapping(..., style="flow")`, or an `entry()`
containing comments, the emitter must honor that metadata even though the node
is dirty. Explicit formatting supplied by constructors will take precedence over
default serialization heuristics as long as the requested form is valid Myml.

This closes the current gap where preservation mostly works for untouched
parsed nodes but not for newly inserted or replaced values.

Alternatives considered:

- Treat constructor metadata as a hint only: rejected because callers need a
  reliable way to request concrete formatting.
- Preserve style only for parsed untouched nodes: rejected because it would
  leave the new constructors ineffective for the main editing scenarios.

## Risks / Trade-offs

- More public surface area for the Python library -> Mitigate by keeping
  ordinary `load`/`dump` and item assignment behavior unchanged for simple use
  cases.
- Constructor and entry APIs may overlap conceptually for new users ->
  Mitigate by documenting the node-vs-entry distinction clearly with examples.
- Placement operations can create ambiguous edge cases -> Mitigate by making
  `reorder(keys)` require a complete key set and by rejecting invalid
  `insert(before=..., after=...)` combinations.
- Backward-compatible naming may leave some tension between "roundtrip" and
  "format-aware" terminology -> Mitigate by treating `roundtrip` as the parse
  option and "format-aware" as the editing model in docs and examples.

## Migration Plan

1. Add public constructors and wrapper types without removing existing
   roundtrip entry points.
2. Teach roundtrip wrappers and upgraded wrappers to accept node constructors,
   `entry()` values, and placement operations.
3. Update emission and dirty-node handling so explicit style metadata is
   preserved for edited content.
4. Add corpus and library tests for constructor-based formatting injection,
   entry comments, and placement operations.
5. Document the new APIs as the preferred advanced editing surface while
   keeping existing roundtrip workflows valid.

## Open Questions

- Should the library export renamed wrapper class names such as
  `FormatMapping` and `FormatSequence`, or only describe the behavior as
  format-aware while keeping the existing class names?
- Should `entry(before=...)` accept raw comment strings with `#` markers,
  normalized comment text without `#`, or both?
- Should sequence item access use `item(index)`, `entry(index)`, or another
  name that best matches the mapping-side API?
