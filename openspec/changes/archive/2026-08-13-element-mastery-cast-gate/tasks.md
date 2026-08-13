## 1. Pure functions

- [x] 1.1 Add `magic_rank_title(entity) -> str` to `world/rules/progression.py` with the five-band
      constant table
- [x] 1.2 Add `can_cast_spell_tier(entity, element, tier) -> bool` to `world/rules/progression.py`,
      checking numeric level against the band, or direct ownership of `f"{element}_mastery"` via
      `entity.skills.owned_keys()` (never `conferred_grants()`)
- [x] 1.3 Unit tests for both functions per the `element-mastery` spec's scenarios
- [x] 1.4 Add `spell_tier_for(skill) -> str | None` to `world/skills/cost_tiers.py`: classify an
      ACTIVE skill carrying both an element and an `mp` cost into the unique §4.3 tier band (prefer
      the target-spec column, fall back to the other), with unit tests incl. the `SELF` and
      non-spell cases

## 2. Four new mastery skills

- [x] 2.1 Add `water_mastery`, `earth_mastery`, `lightning_mastery`, `ice_mastery` to
      `world/skills/registry.py`, matching the existing four mastery skills' construction pattern

## 3. Wire into action resolution

- [x] 3.1 Read `ActionResolver.preflight`/`resolve`'s existing skill-ownership/kind validation step in
      full before editing
- [x] 3.2 Add the `can_cast_spell_tier` check to that same step (not a new step), reusing the existing
      rejection category; a malformed elemental spell (missing/non-positive/out-of-band `mp` cost)
      fails closed into the same rejection instead of passing ungated
- [x] 3.3 Run the full existing `action-resolution-pipeline` scenario suite; confirm no regression
- [x] 3.4 Filter `monster_behaviour_policy`'s candidate damage skills through the same gate, with
      tests for a magic-level-0 monster (falls back to the innate physical attack) and a monster
      with direct mastery (spell remains selectable)

## 4. Tests

- [x] 4.1 Preflight rejection test for an under-tier cast without mastery
- [x] 4.2 Preflight success test via numeric level alone
- [x] 4.3 Preflight success test via mastery ownership alone, at magic_level 1
