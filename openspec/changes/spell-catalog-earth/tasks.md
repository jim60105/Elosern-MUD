## 1. Prerequisite confirmation

- [ ] 1.1 Confirm `skill-effects-typed-model` has landed and `world/skills/effects.py`'s typed dispatch table exists — every effect string this change adds must parse under it.
- [ ] 1.2 Confirm `element-mastery-cast-gate` has landed and `can_cast_spell_tier(entity, element, tier)` exists in `world/rules/progression.py`, along with the `earth_mastery` skill this element needs.

## 2. Registry entries

- [ ] 2.1 Add 10 new `_skill(...)` entries to `SKILL_REGISTRY` in `world/skills/registry.py` for: `stone_shard`, `hardened_skin`, `stone_armor`, `dust_veil`, `earth_bind`, `rockslide`, `earthquake`, `earthen_ward`, `mountain_collapse`, `earths_judgment`.
- [ ] 2.2 Group the ten entries in registry-literal order as five tier-labeled pairs (學徒/術師/大師/賢者/主宰) with a `# 土 — <tier>` comment above each pair, matching this change's `design.md` Decisions section.
- [ ] 2.3 Set each entry's `key`, `label`, `description` (new Traditional Chinese flavor text consistent with §4.4's naming), `kind=SkillKind.ACTIVE`, `target_spec`, `cost`, `element`, and `effects` exactly per this change's `design.md` table — do not invent different numbers or names.
- [ ] 2.4 Run `python -c "from world.skills.registry import SKILL_REGISTRY"` (once `skill-effects-typed-model` has landed) to confirm every new `effects` string parses without raising at import time.

## 3. buffs.yaml additions

- [ ] 3.1 Add a `earth_hardened_skin` row to `world/rules/rulebook/buffs.yaml`: self defense buff (rate/bounds-shaped defense increase), applied by `hardened_skin`.
- [ ] 3.2 Add a `earth_stone_armor` row to `world/rules/rulebook/buffs.yaml`: shield buff (defense bounds ceiling), applied by `stone_armor`.
- [ ] 3.3 Add a `earth_dust_veil` row to `world/rules/rulebook/buffs.yaml`: accuracy-down debuff (bounds-shaped accuracy reduction), applied by `dust_veil`.
- [ ] 3.4 Add a `earth_root` row to `world/rules/rulebook/buffs.yaml`: marker control buff (empty `modifiers`, same shape as `paralysis`/`fear`) representing 束縛, applied by `earth_bind`.
- [ ] 3.5 Add a `earth_ward` row to `world/rules/rulebook/buffs.yaml`: party shield buff (defense bounds ceiling), applied by `earthen_ward`.
- [ ] 3.6 Confirm every new row uses only `rate`/`bounds`/`decay` keys under `modifiers` and configures no combat-stat multiplier, per `buff-handler-integration`'s existing constraint.

## 4. Tests

- [ ] 4.1 Extend the registry-level parametrized round-trip test (design doc §9) to cover all ten 土 spells' `effects` strings.
- [ ] 4.2 Add tier-boundary tests for 土's four tier thresholds (magic level 15/16, 30/31, 70/71, 90/91) confirming `can_cast_spell_tier` rejects without `earth_mastery` and permits with it, per this change's `specs/skill-registry/spec.md`.
- [ ] 4.3 Add/extend `buffs.yaml` fixture tests covering the new row(s) added in task group 3, following the existing `poisoned`/`paralysis`/`fear` test style.

## 5. Recost pre-existing anchor skill

- [ ] 5.1 N/A — 土 has no pre-existing anchor skill to recost; all ten entries are new.
