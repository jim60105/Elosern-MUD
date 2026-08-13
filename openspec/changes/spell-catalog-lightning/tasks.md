## 1. Prerequisite confirmation

- [x] 1.1 Confirm `skill-effects-typed-model` has landed and `world/skills/effects.py`'s typed dispatch table exists — every effect string this change adds must parse under it.
- [x] 1.2 Confirm `element-mastery-cast-gate` has landed and `can_cast_spell_tier(entity, element, tier)` exists in `world/rules/progression.py`, along with the `lightning_mastery` skill this element needs.

## 2. Registry entries

- [x] 2.1 Add 10 new spell entries to `SKILL_REGISTRY` in `world/skills/registry.py` for: `spark_shock`, `static_ward`, `chain_lightning`, `paralyzing_bolt`, `thunder_combo`, `lightning_strike`, `heavens_thunder`, `thunder_gods_haste`, `judgement_thunder`, `divine_lightning_slaughter` — eight via the `_elemental_spells` builder, plus `static_ward`/`thunder_gods_haste` as explicit `_skill(...)` calls with `FactionConstraint.SELF_ONLY` (their `self_buff_apply` effects are inherently self-only, which the builder's fixed `ANY` would contradict).
- [x] 2.2 Group the entries in registry-literal order as five tier-labeled pairs (學徒/術師/大師/賢者/主宰) with a `# 雷 — <tier>` comment above each pair; `static_ward` (學徒) and `thunder_gods_haste` (賢者) sit under their tier comments directly after the lightning builder block, matching this change's `design.md` Decisions section.
- [x] 2.3 Set each entry's `key`, `label`, `description` (new Traditional Chinese flavor text consistent with §4.4's naming), `kind=SkillKind.ACTIVE`, `target_spec`, `cost`, `element`, and `effects` exactly per this change's `design.md` table — do not invent different numbers or names.
- [x] 2.4 Run `python -c "from world.skills.registry import SKILL_REGISTRY"` (once `skill-effects-typed-model` has landed) to confirm every new `effects` string parses without raising at import time.

## 3. buffs.yaml additions

- [x] 3.1 Add a `lightning_static_ward` row to `world/rules/rulebook/buffs.yaml`: self counter-attack buff (bounds-shaped defense increase), applied by `static_ward`.
- [x] 3.2 Add a `lightning_extra_action` row to `world/rules/rulebook/buffs.yaml`: self extra-action buff (bounds-shaped `actions_per_turn` increase), applied by `thunder_gods_haste`.
- [x] 3.3 Confirm the existing `paralysis` row in `buffs.yaml` still matches this element's reuse case (麻痺電擊 (`paralyzing_bolt`) reuses the existing `paralysis` buff row exactly — no new row needed, matching this element's 麻痺 flavor precisely) — no new row needed.
- [x] 3.4 Confirm every new row uses only `rate`/`bounds`/`decay` keys under `modifiers` and configures no combat-stat multiplier, per `buff-handler-integration`'s existing constraint.
- [x] 3.5 Add the matching `lightning_static_ward`/`lightning_extra_action` rows to `world/rules/rulebook/status_display.yaml` (Traditional Chinese label + severity) — its fail-closed coverage requires every buff key to have exactly one display entry, so a new buff key without one breaks module import.

## 4. Tests

- [x] 4.1 Extend the registry-level parametrized round-trip test (design doc §9) to cover all ten 雷 spells' `effects` strings.
- [x] 4.2 Add tier-boundary tests for 雷's four tier thresholds (magic level 15/16, 30/31, 70/71, 90/91) confirming `can_cast_spell_tier` rejects without `lightning_mastery` and permits with it, per this change's `specs/skill-registry/spec.md`.
- [x] 4.3 Add/extend `buffs.yaml` fixture tests covering the new row(s) added in task group 3, following the existing `poisoned`/`paralysis`/`fear` test style.

## 5. Recost pre-existing anchor skill

- [x] 5.1 N/A — 雷 has no pre-existing anchor skill to recost; all ten entries are new.
