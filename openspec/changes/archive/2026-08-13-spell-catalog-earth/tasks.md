## 1. Prerequisite confirmation

- [x] 1.1 Confirm `skill-effects-typed-model` has landed and `world/skills/effects.py`'s typed dispatch table exists — every effect string this change adds must parse under it.
- [x] 1.2 Confirm `element-mastery-cast-gate` has landed and `can_cast_spell_tier(entity, element, tier)` exists in `world/rules/progression.py`, along with the `earth_mastery` skill this element needs.

## 2. Registry entries

- [x] 2.1 Add 10 new spell entries to `SKILL_REGISTRY` in `world/skills/registry.py` for: `stone_shard`, `hardened_skin`, `stone_armor`, `dust_veil`, `earth_bind`, `rockslide`, `earthquake`, `earthen_ward`, `mountain_collapse`, `earths_judgment` — nine via the `_elemental_spells` builder, plus `hardened_skin` as an explicit `_skill(...)` call with `FactionConstraint.SELF_ONLY` (its `self_buff_apply` effect is inherently self-only, which the builder's fixed `ANY` would contradict).
- [x] 2.2 Group the entries in registry-literal order as five tier-labeled pairs (學徒/術師/大師/賢者/主宰) with a `# 土 — <tier>` comment above each pair; `hardened_skin` sits under the 學徒 comment directly after the earth builder block, matching this change's `design.md` Decisions section.
- [x] 2.3 Set each entry's `key`, `label`, `description` (new Traditional Chinese flavor text consistent with §4.4's naming), `kind=SkillKind.ACTIVE`, `target_spec`, `cost`, `element`, and `effects` exactly per this change's `design.md` table — do not invent different numbers or names.
- [x] 2.4 Run `python -c "from world.skills.registry import SKILL_REGISTRY"` (once `skill-effects-typed-model` has landed) to confirm every new `effects` string parses without raising at import time.

## 3. buffs.yaml additions

- [x] 3.1 Add a `earth_hardened_skin` row to `world/rules/rulebook/buffs.yaml`: self defense buff (rate/bounds-shaped defense increase), applied by `hardened_skin`.
- [x] 3.2 Add a `earth_stone_armor` row to `world/rules/rulebook/buffs.yaml`: shield buff (defense bounds ceiling), applied by `stone_armor`.
- [x] 3.3 Add a `earth_dust_veil` row to `world/rules/rulebook/buffs.yaml`: accuracy-down debuff (bounds-shaped accuracy reduction), applied by `dust_veil`.
- [x] 3.4 Add a `earth_root` row to `world/rules/rulebook/buffs.yaml`: marker control buff (empty `modifiers`, same shape as `paralysis`/`fear`) representing 束縛, applied by `earth_bind`.
- [x] 3.5 Add a `earth_ward` row to `world/rules/rulebook/buffs.yaml`: party shield buff (defense bounds ceiling), applied by `earthen_ward`.
- [x] 3.6 Confirm every new row uses only `rate`/`bounds`/`decay` keys under `modifiers` and configures no combat-stat multiplier, per `buff-handler-integration`'s existing constraint.
- [x] 3.7 Add the matching `earth_hardened_skin`/`earth_stone_armor`/`earth_dust_veil`/`earth_root`/`earth_ward` rows to `world/rules/rulebook/status_display.yaml` (Traditional Chinese label + severity) — its fail-closed coverage requires every buff key to have exactly one display entry, so a new buff key without one breaks module import.

## 4. Tests

- [x] 4.1 Extend the registry-level parametrized round-trip test (design doc §9) to cover all ten 土 spells' `effects` strings.
- [x] 4.2 Add tier-boundary tests for 土's four tier thresholds (magic level 15/16, 30/31, 70/71, 90/91) confirming `can_cast_spell_tier` rejects without `earth_mastery` and permits with it, per this change's `specs/skill-registry/spec.md`.
- [x] 4.3 Add/extend `buffs.yaml` fixture tests covering the new row(s) added in task group 3, following the existing `poisoned`/`paralysis`/`fear` test style.

## 5. Recost pre-existing anchor skill

- [x] 5.1 N/A — 土 has no pre-existing anchor skill to recost; all ten entries are new.
