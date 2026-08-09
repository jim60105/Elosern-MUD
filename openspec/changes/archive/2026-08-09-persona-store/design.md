# persona-store — Design

## Context

`typeclasses/entities.py:28` declares `persona: Any | None = AttributeProperty(default=None)` as a
placeholder seam; `world/imports/loader.py` stores validated persona dicts verbatim on
`entity.db.persona`. No module reads persona. The `living-entity-hierarchy` main spec keeps the
seam declared (its "no PersonaStore class definition" scenario locks the placeholder). The
persona-dialogue design (`docs/superpowers/specs/2026-08-09-persona-dialogue-design.md`) requires
a read-only handler that retrieves fields by key and flattens them into bounded prompt blocks, and
will consume this change as its foundation. Only the persist half exists today; this change adds
retrieve and flatten.

Constraints:

- `world/rules/` is the primary deterministic package; a read-only helper there is consistent with
  existing read models (`status_query.py`, `combat_view.py`).
- `world/ai/` must never write; this module has no write path at all.
- Adult invariant and single-writer boundary must not be weakened.
- No migration or backward compatibility (unreleased project).

## Goals / Non-Goals

**Goals:**

- Provide `PersonaStore`, a read-only handler over an entity's verbatim persona record.
- Flatten exactly `personality`, `life_story`, and `habit` into one bounded, labeled prompt block.
- Mount it on `LivingEntity.persona` following the `relations` mount pattern.
- Flip the `living-entity-hierarchy` persona-seam requirement with a `MODIFIED` delta.

**Non-Goals:**

- Any write path (import loader stays the only writer).
- Persona content interpretation, schema validation, or filtering (authored content is opaque).
- Prompt injection (owned by the `persona-dialogue-injection` change).
- Behavior change for existing characters (persona remains absent until future changes supply it).

## Decisions

### D1: Handler location and mount — `world/rules/persona.py`, mounted as `LivingEntity.persona`

`PersonaStore` lives in `world/rules/persona.py` and is mounted via `lazy_property` on
`LivingEntity.persona`, replacing the `AttributeProperty` — the identical pattern `relations`
(`world/rules/affinity.py::RelationHandler`) uses. Raw data stays at `entity.db.persona`.

- Alternatives considered: keeping the raw attribute and mounting under a new name (e.g.
  `persona_store`). Rejected: the master design explicitly reserves the bare `entity.persona` name
  for the handler, and the import-loader scenario wording ("leaving the bare `entity.persona` name
  free for the PersonaStore handler to mount on") anticipates exactly this flip.
- Note: `entity.db.persona` (attribute-store access) and `entity.persona` (descriptor) diverge
  after the flip by design; the loader's `db` path is untouched.

### D2: Flatten contract — three fields, labeled sections, caps

`flatten(fields=("personality", "life_story", "habit")) -> str | None` and
`get(field: str) -> Any | None`:

- `get` returns the stored value verbatim for an existing key; `None` for a missing key, a
  non-mapping record, or a missing record — never raising. Evennia materializes stored persona
  dicts as dbserialize mapping wrappers, so any `Mapping` counts as a record.
- `flatten` emits one labeled section per present field in declared field order (性格：… /
  人生經歷：… / 習慣：…). Only non-empty `str` fields produce a section; `None`, numeric, or
  container values are treated as absent — never raising.
- Per-field string cap and a combined block cap, following the project's `_cap_string` idiom for
  LLM-bound text. The constructor validates both caps as positive integers and raises `ValueError`
  on invalid configuration (a programming error); the record-data truncation path itself never
  raises.
- Missing record, non-mapping record, or no section-producing fields → `None` (no block), never an
  exception.
- Field order and caps are call-site-configurable so the dialogue-injection change can adjust them
  without touching this module's behavior.

- Alternatives considered: per-field dict return for structured payloads. Rejected: the first
  consumer (dialogue injection) needs a text block; a dict return adds an unused serialization
  decision. Structured fields remain a future seam.

### D3: No write API, no imports of writers

`PersonaStore` exposes only reads. It imports no state-mutating module and never touches
`entity.traits`, attributes beyond the single persona record, or the clock. The module docstring
and a zero-write assertion test pin this.

## Risks / Trade-offs

- [Descriptor flip could surprise callers expecting an attribute value] → Only `imports/loader.py`
  writes persona, via the `db` path; repository-wide grep during implementation confirms no other
  reader exists. Existing characters have `persona = None`, which the mount preserves (handler with
  no record returns `None` from `flatten`).
- [Flatten caps truncate authored content silently] → Documented behavior; truncation is
  deterministic and bounded, matching the project's approach to LLM-bound text.
- [Over-long persona blocks could balloon later prompt payloads] → Total block cap is enforced in
  the handler; the injection change adds its own serialization bounds on top.

## Migration Plan

No data migration. The attribute storage (`entity.db.persona`) is unchanged; only the class-level
descriptor flips. Rollback is a revert of the mount edit.

## Open Questions

- None blocking. Whether future consumers want per-field structured output is deferred; the
  call-site-configurable `fields` parameter is the seam.
