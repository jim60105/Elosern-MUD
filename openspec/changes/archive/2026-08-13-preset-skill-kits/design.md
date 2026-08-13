## Context

`PlayerPreset` is a frozen dataclass registry in `world/lore/player_presets.py` mirroring the
import-card identity shape (key, display_name, age, apparent_age, race, subrace, allocations,
emphasis, background). Activation (`world/rules/character_creation.py::activate_player_character`)
derives identity and trait values from a preset, samples magic level inside the race band, and
writes initial mechanical state inside one atomic transaction — including `skills` which is
currently hardcoded to `{"active": [], "passive": []}`. The `skills` key is already part of
`_CREATION_ATTRIBUTE_KEYS`, so the existing snapshot/restore rollback machinery covers it.

The skill-system redesign landed a complete `SKILL_REGISTRY` (`world/skills/registry.py`) with
load-time validation: unknown effect prefixes, overlong metadata, and duplicate stat multipliers
all raise at import. `SkillKind.ACTIVE` / `SkillKind.PASSIVE` and `SkillDef.requires_divine_arts`
(the cast gate in `world/rules/action.py`) are the classification surface a preset kit must satisfy.

## Goals / Non-Goals

**Goals:**
- Presets carry a declared active/passive skill kit, granted by activation in the same atomic
  transaction as the rest of the creation write.
- Invalid preset kits fail at module load, mirroring the skill registry's load-time validation
  style; a player can never activate a preset with an unowned/invalid skill.
- Ship exactly 8 template characters (the WebClient card contract allows at most 8), all female,
  adult (age/apparent_age ≥ 18 per the hard invariant), with distinct roles, distinct kits,
  budget-exact allocations, and lore-consistent backgrounds.
- Custom-created characters keep starting with innate skills only.

**Non-Goals:**
- No WebClient/presentation change: the `creation` panel card contract stays byte-identical
  (skills must NOT be exposed).
- No skill registry changes: every kit references existing `SKILL_REGISTRY` keys.
- No import-card schema change: imports already support `skills`/`passives`; presets are a
  separate registry.
- No balance overhaul of elf physical bands or magic-level sampling.

## Decisions

**D1. Dataclass shape.** `PlayerPreset` gains `active_skills: tuple[str, ...] = ()` and
`passive_skills: tuple[str, ...] = ()`, plus `skill_lists() -> dict[str, list[str]]` producing the
exact storage shape `{"active": [...], "passive": [...]}` in declared order. Two separate tuples
are clearer than a nested structure and match the import-card `skills`/`passives` split.

**D2. Load-time validation.** A module-level validation pass (executed at import, after the
registry literal is built) raises `ValueError` when a preset declares: a key absent from
`SKILL_REGISTRY`; an active key whose registry `SkillKind` is not `ACTIVE` (or passive not
`PASSIVE`); or a `requires_divine_arts` skill on a preset whose race lacks `can_use_divine_arts`
(the same gate the action resolver enforces at cast time, `world/rules/action.py`). Activation
needs no re-validation beyond what preflight already does, keeping the single source of truth in
the registry.

**D3. Activation write.** `preflight_character_creation` resolves the preset as today;
`activate_player_character` replaces the empty `skills` literal with `preset.skill_lists()` when
`request.mode == "preset"`, and keeps the empty shape for custom mode. The write goes through the
same `attributes.add` loop inside the same `transaction.atomic()`, so rollback behavior, portrait
finalization, and draft clearing are unchanged. `skill_grants` stays empty.

**D4. Catalog content design rules.** The 8 entries follow the story cast
(`tmp/story_settings/character/*`, `world_info.md`) with adult-adjusted ages (story ages 14–16 and
the eternal-10 Eolas appearance cannot satisfy the ≥ 18 invariant; the Eolas subrace is therefore
not used). Each kit is unique except the single `light_sword_style` shared by the two human sword
users (the only single-sword active skill in the registry); roles, allocations, and backgrounds
are distinct per character. Allocations must sum exactly to `resolve_starting_profile(...).budget`
(human 181, beastfolk 105, elf 37) — the existing lore test enforces this.

**D5. Test strategy.**
- Extend `world/lore/tests/test_player_presets.py`: every declared skill key resolves in
  `SKILL_REGISTRY` with matching `SkillKind`; divine-arts skills only on `can_use_divine_arts`
  races; catalog ships exactly 8 presets; race coverage + budget/bounds assertions stay.
- Extend `world/rules/tests/test_character_creation.py`: preset activation persists the preset's
  kit into `character.db.skills` and clears `creation_draft`; custom activation leaves
  `{"active": [], "passive": []}`; the new requirement gets a `covers_requirement` annotation.
- Update exact-key-list assertions (`web/webclient/presentation/tests/test_creation_panel.py`
  lines ~95–106) to the 8-key ordering; keep `human_wanderer` first so browser tests that press
  Enter on the first card keep working.

## Risks / Trade-offs

- **Power disparity between presets:** elf presets (悠花/悠奈/伊洛希雅) carry mastery skills and
  ×100/×1000 body-enhancement passives from their story sheets. This is intentional world design
  (elves are the power archetype) but makes elf presets strictly stronger than human/beastfolk
  starters; the story cast mandates it, and the WebClient UI groups all presets equally.
- **Content coupling:** the catalog is now at the UI spec's "at most 8" cap; any future addition
  requires an OpenSpec change to `webclient-character-creation-ui`. Removing/renaming a preset key
  breaks the hardcoded test list — keys are treated as stable public surface.
- **Eolas excluded:** the 幻童精靈 subrace cannot ship as a preset under the adult invariant; if
  that changes someday, a preset for it becomes possible without this change's approval.
