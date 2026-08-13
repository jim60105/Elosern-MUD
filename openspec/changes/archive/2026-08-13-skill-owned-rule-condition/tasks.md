## 1. Condition primitive

- [x] 1.1 Add `skill_owned` handling to `evaluate_condition()` in `world/rules/rulebook/schema.py`
- [x] 1.2 Ensure `combat_modifiers.py`'s context builder exposes whatever `evaluate_condition` needs to
      check `entity.skills.owned_keys()` (likely just passing `entity` through, matching how
      `buff_active` already resolves against the entity)

## 2. Seed data

- [x] 2.1 Add a `skill_owned` row for `defense_instinct` (small flat `defense` bonus)
- [x] 2.2 Add a `skill_owned` row for `blade_art_mastery` (bonus to blade/sword-family skill damage or
      accuracy — pick the closest existing adjustment field)
- [x] 2.3 Add a `skill_owned` row for `extreme_endurance` (SP-cost reduction or SP-regen bonus)
- [x] 2.4 Add a `skill_owned` row for `magic_circle_comprehension` (spell accuracy or MP-cost reduction)
- [x] 2.5 Add a `skill_owned` row for `precise_mana_control` (MP-cost reduction, distinct from 2.4's
      field so the two don't collapse into the same adjustment)
- [x] 2.6 Add a `skill_owned` row for `retainer_martial_training` (small flat `atk_phys`/`defense`
      bonus, retainer/companion-flavored)
- [x] 2.7 Add a `skill_owned` row for `guardian_instinct` (bonus when protecting/covering an ally, or a
      flat `defense` bonus if no "protect" mechanic exists to hook into)
- [x] 2.8 Add a `skill_owned` row for `reincarnation_boon_yuka` (`combat_prediction:武感` — initiative or
      evasion/accuracy bonus)
- [x] 2.9 Document each row's flavor-to-mechanic mapping rationale as an inline YAML comment
- [x] 2.10 Add the mandatory `test_rule_<id>` function for each of the 8 new rule IDs, per the landed
      `combat-modifier-table` spec's existing hard requirement that every `combat_modifiers.yaml` rule
      ID have exactly one corresponding test function — CI enforces this correspondence, so it must not
      be skipped

## 3. Tests

- [x] 3.1 Per-skill test: owning it produces its adjustment; not owning it does not
- [x] 3.2 Merge test: an entity with a skill_owned row active plus an existing buff-origin and
      sexual-origin row active gets all three merged with no special-casing
- [x] 3.3 Confirm no test anywhere still asserts these eight skills are inert (update/remove any that
      do)
