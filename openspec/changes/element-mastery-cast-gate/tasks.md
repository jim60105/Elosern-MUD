## 1. Pure functions

- [ ] 1.1 Add `magic_rank_title(entity) -> str` to `world/rules/progression.py` with the five-band
      constant table
- [ ] 1.2 Add `can_cast_spell_tier(entity, element, tier) -> bool` to `world/rules/progression.py`,
      checking numeric level against the band, or direct ownership of `f"{element}_mastery"` via
      `entity.skills.owned_keys()` (never `conferred_grants()`)
- [ ] 1.3 Unit tests for both functions per the `element-mastery` spec's scenarios

## 2. Four new mastery skills

- [ ] 2.1 Add `water_mastery`, `earth_mastery`, `lightning_mastery`, `ice_mastery` to
      `world/skills/registry.py`, matching the existing four mastery skills' construction pattern

## 3. Wire into action resolution

- [ ] 3.1 Read `ActionResolver.preflight`/`resolve`'s existing skill-ownership/kind validation step in
      full before editing
- [ ] 3.2 Add the `can_cast_spell_tier` check to that same step (not a new step), reusing the existing
      rejection category
- [ ] 3.3 Run the full existing `action-resolution-pipeline` scenario suite; confirm no regression

## 4. Tests

- [ ] 4.1 Preflight rejection test for an under-tier cast without mastery
- [ ] 4.2 Preflight success test via numeric level alone
- [ ] 4.3 Preflight success test via mastery ownership alone, at magic_level 1
