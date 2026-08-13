## 1. Prerequisite confirmation

- [ ] 1.1 Confirm `skill-effects-typed-model` has landed and `world/skills/effects.py`'s typed dispatch table exists — every effect string this change adds must parse under it.
- [ ] 1.2 Confirm `element-mastery-cast-gate` has landed and `can_cast_spell_tier(entity, element, tier)` exists in `world/rules/progression.py`, along with the `wind_mastery` skill this element needs.
- [ ] 1.3 Confirm `movement-skill-waiver` has landed and `flight` is already reclassified `PASSIVE` with its `wilderness_move` waiver wired into `charge_movement()` — this change's `flight` MP recost (task 5.2) edits that same entry and should not run before this reclassification exists.

## 2. Registry entries

- [ ] 2.1 Add 8 new spell entries to `SKILL_REGISTRY` in `world/skills/registry.py` (via the `_elemental_spells` builder) for: `gale_step`, `tornado_blade`, `storm_domain`, `gale_dance_strike`, `heavens_wrath_storm`, `haste_domain`, `vacuum_severance`, `sky_tempest`.
- [ ] 2.2 Group the ten entries in registry-literal order as five tier-labeled pairs (學徒/術師/大師/賢者/主宰) with a `# 風 — <tier>` comment above each pair, matching this change's `design.md` Decisions section.
- [ ] 2.3 Set each entry's `key`, `label`, `description` (new Traditional Chinese flavor text consistent with §4.4's naming), `kind=SkillKind.ACTIVE`, `target_spec`, `cost`, `element`, and `effects` exactly per this change's `design.md` table — do not invent different numbers or names.
- [ ] 2.4 Run `python -c "from world.skills.registry import SKILL_REGISTRY"` (once `skill-effects-typed-model` has landed) to confirm every new `effects` string parses without raising at import time.

## 3. buffs.yaml additions

- [ ] 3.1 Add a `wind_haste` row to `world/rules/rulebook/buffs.yaml`: self speed buff (rate/bounds-shaped agility increase), applied by `gale_step`.
- [ ] 3.2 Add a `wind_haste_domain` row to `world/rules/rulebook/buffs.yaml`: party speed+evasion buff (broader bounds than `wind_haste`), applied by `haste_domain`.
- [ ] 3.3 Confirm every new row uses only `rate`/`bounds`/`decay` keys under `modifiers` and configures no combat-stat multiplier, per `buff-handler-integration`'s existing constraint.

## 4. Tests

- [ ] 4.1 Extend the registry-level parametrized round-trip test (design doc §9) to cover all ten 風 spells' `effects` strings.
- [ ] 4.2 Add tier-boundary tests for 風's four tier thresholds (magic level 15/16, 30/31, 70/71, 90/91) confirming `can_cast_spell_tier` rejects without `wind_mastery` and permits with it, per this change's `specs/skill-registry/spec.md`.
- [ ] 4.3 Add/extend `buffs.yaml` fixture tests covering the new row(s) added in task group 3, following the existing `poisoned`/`paralysis`/`fear` test style.

## 5. Recost pre-existing anchor skill

- [ ] 5.1 Edit `wind_blade`'s `cost` in place from `{'mp': 24}` to `{'mp': 14}` — do not duplicate the entry, do not change any other field.
- [ ] 5.2 Edit `flight`'s `cost` in place from `{'mp': 10}` to `{'mp': 22}` — do not duplicate the entry, do not change any other field.
- [ ] 5.3 Confirm no other code or test hardcodes `wind_blade` or `flight`'s old MP cost.
