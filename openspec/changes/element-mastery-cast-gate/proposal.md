## Why

`element_mastery_rank` has no consumer today — the four existing "XX精通" skills
(`fire_mastery`/`dark_mastery`/`wind_mastery`/`light_mastery`) do nothing. World lore defines five
numeric magic-level bands with title names (學徒/術師/大師/賢者/主宰) and states that mastery of an
element means the caster can use every spell of that element regardless of numeric level. Per the
approved design doc (D4, D5, §4.1–§4.2), this needs two independent pure functions: a display-only
rank-title function, and a mechanical cast-gate function — plus the four missing mastery skills
(water/earth/lightning/ice) to bring element coverage to all eight.

## What Changes

- Add `magic_rank_title(entity) -> str` to `world/rules/progression.py`: pure function of
  `entity.traits.magic_level.value` against the five documented bands, for display only.
- Add `can_cast_spell_tier(entity, element, tier) -> bool` to `world/rules/progression.py`: `True` if
  the entity's magic level meets the tier's band threshold, **or** `True` unconditionally if the entity
  owns that element's `<element>_mastery` skill (checked via direct ownership only — conferred grants
  do not satisfy this, per `conferral-generalization`'s explicit exclusion).
- Wire `can_cast_spell_tier` into the action-resolution pipeline's existing skill-ownership/kind
  validation step (`ActionResolver.preflight`/`resolve`), reusing the existing rejection category for
  "may not cast this" rather than adding a new `RejectReason`.
- Add `water_mastery`, `earth_mastery`, `lightning_mastery`, `ice_mastery` to `SKILL_REGISTRY`, matching
  the existing four mastery skills' shape (`PASSIVE`, `ElementMasteryEffect`).

## Capabilities

### New Capabilities
- `element-mastery`: the rank-title and cast-gate pure functions and their bounded, documented
  behavior.

### Modified Capabilities
- `skill-registry`: four new mastery skills.
- `action-resolution-pipeline`: preflight/resolve now additionally reject a spell cast that fails
  `can_cast_spell_tier`, using the existing ownership-style rejection category.

## Impact

- `world/rules/progression.py` (two new pure functions), `world/skills/registry.py` (four new skills),
  `world/rules/action.py` or wherever `ActionResolver` lives (one new gate check in an existing
  validation step).
- Depends on `skill-effects-typed-model` (uses `ElementMasteryEffect`).
- Every `spell-catalog-*` proposal depends on this change landing first, since each new spell's
  tier-gated castability relies on `can_cast_spell_tier`.
