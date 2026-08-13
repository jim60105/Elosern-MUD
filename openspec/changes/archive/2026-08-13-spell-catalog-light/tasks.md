## 1. Prerequisite confirmation

- [x] 1.1 Confirm `skill-effects-typed-model` has landed and `world/skills/effects.py`'s typed dispatch table exists — every effect string this change adds must parse under it.
- [x] 1.2 Confirm `element-mastery-cast-gate` has landed and `can_cast_spell_tier(entity, element, tier)` exists in `world/rules/progression.py`, along with the `light_mastery` skill this element needs.
- [x] 1.3 Confirm `heal-effect-handler` has landed and record its final `heal:<...>` effect-ID grammar; if it differs from this change's provisional `heal:<single|area>` guess, update every affected spell's `effects` entry to match before merging.
- [x] 1.4 Confirm `cleanse-effect-handler` has landed (already raised as its own OpenSpec change) and that `purify`'s `effects=["cleanse:status"]` matches its settled `cleanse:<scope>` grammar exactly; adjust if the landed grammar differs from `cleanse:status`.

## 2. Registry entries

- [x] 2.1 Add 10 new spell entries to `SKILL_REGISTRY` in `world/skills/registry.py` (via the `_elemental_spells` builder) for: `heal`, `light_arrow`, `purify`, `mass_heal`, `advanced_heal`, `holy_shield`, `holy_radiance`, `revival_light`, `goddess_blessing`, `heavens_judgment_light`.
- [x] 2.2 Group the ten entries in registry-literal order as five tier-labeled pairs (學徒/術師/大師/賢者/主宰) with a `# 光 — <tier>` comment above each pair, matching this change's `design.md` Decisions section.
- [x] 2.3 Set each entry's `key`, `label`, `description` (new Traditional Chinese flavor text consistent with §4.4's naming), `kind=SkillKind.ACTIVE`, `target_spec`, `cost`, `element`, and `effects` exactly per this change's `design.md` table — do not invent different numbers or names.
- [x] 2.4 Run `python -c "from world.skills.registry import SKILL_REGISTRY"` (once `skill-effects-typed-model` has landed) to confirm every new `effects` string parses without raising at import time.

## 3. buffs.yaml additions

- [x] 3.1 Add a `light_holy_shield` row to `world/rules/rulebook/buffs.yaml`: shield buff (defense bounds ceiling), applied by `holy_shield`.
- [x] 3.2 Add a `light_blessing` row to `world/rules/rulebook/buffs.yaml`: party buff (bounds-shaped multi-stat boost), applied by `goddess_blessing`.
- [x] 3.3 Confirm every new row uses only `rate`/`bounds`/`decay` keys under `modifiers` and configures no combat-stat multiplier, per `buff-handler-integration`'s existing constraint.
- [x] 3.4 Add the matching `light_holy_shield`/`light_blessing` rows to `world/rules/rulebook/status_display.yaml` (Traditional Chinese label + severity) — its fail-closed coverage requires every buff key to have exactly one display entry, so a new buff key without one breaks module import.

## 4. Tests

- [x] 4.1 Extend the registry-level parametrized round-trip test (design doc §9) to cover all ten 光 spells' `effects` strings.
- [x] 4.2 Add tier-boundary tests for 光's four tier thresholds (magic level 15/16, 30/31, 70/71, 90/91) confirming `can_cast_spell_tier` rejects without `light_mastery` and permits with it, per this change's `specs/skill-registry/spec.md`.
- [x] 4.3 Add/extend `buffs.yaml` fixture tests covering the new row(s) added in task group 3, following the existing `poisoned`/`paralysis`/`fear` test style.

## 5. Recost pre-existing anchor skill

- [x] 5.1 N/A — 光 has no pre-existing anchor skill to recost; all ten entries are new.
