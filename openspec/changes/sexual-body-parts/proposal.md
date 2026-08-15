## Why

The forthcoming sexual act system needs a fixed vocabulary of body parts to key
`SexualState.sensitivity` by (already a per-part mapping, already exported from this same module as
`SENSITIVITY_LEVELS`) and a single sentinel value that any `Monster` target collapses to, so no
per-archetype anatomy table is ever built or maintained
(`docs/superpowers/specs/2026-08-15-sexual-act-system-overview-design.md` D-8;
`docs/superpowers/specs/2026-08-15-sexual-act-resolution-design.md` §1). Neither vocabulary exists
today. This change adds the constants only — no behavior reads them yet.

## What Changes

- Extend `world/lore/sexual_vocab.py` with two new module-level exports: `BODY_PARTS` (a 10-member
  tuple of Traditional Chinese body-part names) and `GENERIC_BODY_PART` (a single sentinel string,
  `"軀體"`), following the module's existing no-behavior, no-`world/rules/`-or-`world/imports/`
  -dependency constraint.
- `GENERIC_BODY_PART` is deliberately **not** a member of `BODY_PARTS`, so "no act may declare the
  generic channel as one of its own parts" is a structural test against tuple membership, not a
  convention a future author has to remember.
- Update the module docstring to describe both vocabulary groups and their consumers: the six
  existing ordered-level tuples' documented current/future consumers are unchanged; `BODY_PARTS` and
  `GENERIC_BODY_PART` have **no current consumer** — they ship ahead of the (separate, later)
  proposals that read them, exactly as the six existing tuples originally shipped ahead of
  `sexual-state`.
- Part resolution logic itself — collapsing a `Monster` target to `GENERIC_BODY_PART` — is **not**
  part of this change. It requires `isinstance(entity, Monster)`, which this module's own spec
  forbids it from depending on (no `world/rules/`, and `Monster` is a `typeclasses/` class); it ships
  in a later, separate proposal (`sexual-act-effects`, referred to as `B5` in the design set).

## Capabilities

### Modified Capabilities
- `sexual-vocabulary`: `world/lore/sexual_vocab.py` gains `BODY_PARTS` and `GENERIC_BODY_PART`, and
  its module-scope and docstring requirements are updated to describe the addition.

## Impact

- **Affected code**: `world/lore/sexual_vocab.py` only.
- **Affected tests**: `world/lore/tests/test_sexual_vocab.py` gains new assertions for `BODY_PARTS`
  and `GENERIC_BODY_PART`; no existing assertion for the six original tuples changes.
- **Not affected**: `world/imports/schema.py` (`CHARACTER_SCHEMA_V1`'s `sexual_baseline.sensitivity`
  property already accepts any string as a part key — `additionalProperties: {"enum":
  list(SENSITIVITY_LEVELS)}` constrains only sensitivity *values*, never keys — so this change adds
  no schema-level key constraint. Constraining `sensitivity`'s keys to `BODY_PARTS` would require
  editing `world/imports/schema.py`, which belongs to a different, file-disjoint proposal
  (`entity-sex-field`, `S1`) running in the same parallel batch as this one; doing so here would
  create exactly the merge conflict the proposal sequence's file-ownership contract exists to
  avoid. See design.md's Non-Goals.
- **Not affected**: `world/rules/sexual_state.py`'s `_SensitivityProxy`, which already defaults any
  unseen part key to `SENSITIVITY_LEVELS[0]` (`"普通"`) without raising — this change requires no
  modification there for `BODY_PARTS` or `GENERIC_BODY_PART` to work once a consumer exists.
- **Downstream consumers**: the later `sexual-act-registry` and `sexual-act-effects` proposals (`B4`
  and `B5` in the sexual-act-system design set) — `SexualActDef`'s `actor_part`/`target_part` fields
  will validate against `BODY_PARTS`, and `resolve_part()` will return `GENERIC_BODY_PART` for any
  `Monster` target. This change ships the vocabulary only.
