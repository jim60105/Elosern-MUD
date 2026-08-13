## Why

The landed skill-system redesign shipped a full `SKILL_REGISTRY` (16 changes: typed effects, 80
spells, mastery skills, 神之秘法 family), but preset character activation still writes empty
`skills` — the shipped template characters cannot carry any of the new skills, and the catalog is
only three presets. New players who pick a preset start with nothing but the innate `basic_attack`
and `flee`, while the skill registry already contains kits designed for the story cast
(`reincarnation_boon_elosia/yuka/yuna`, `guardian_instinct`, `magic_circle_comprehension`, …).

## What Changes

- `PlayerPreset` gains `active_skills` / `passive_skills` frozen tuple fields (empty by default) and
  a `skill_lists()` helper returning the storage shape `{"active": [...], "passive": [...]}`.
- Load-time validation in `world/lore/player_presets.py`: every declared skill key SHALL exist in
  `SKILL_REGISTRY` with the matching `SkillKind`, and a skill requiring divine arts SHALL only be
  declared by a preset whose race `can_use_divine_arts` — an invalid kit raises at import, never at
  player activation.
- Preset activation grants the preset's skill kit: `activate_player_character` writes the preset's
  active/passive keys into the character's `skills` attribute inside the existing all-or-nothing
  transaction (the `skills` key is already in the creation attribute snapshot/restore set). Custom
  activation still starts with no skills beyond the innate set.
- The preset catalog expands from 3 to the spec-allowed maximum of 8 template characters, all
  female, drawing on the story cast (`tmp/story_settings/character/*`): 艾琳, 露芙, 瑟芮雅 (updated
  content + skills) plus 薇歐蕾特, 莉茲婭, 悠花, 悠奈, 伊洛希雅 (new). Each carries a distinct role,
  a distinct skill kit, budget-exact allocations, and a one-line background in the registry
  `background` field. No preset violates the adult invariant (`age`/`apparent_age` ≥ 18); the
  幻童精靈 Eolas subrace is deliberately not used because its eternal-10 appearance cannot satisfy
  the invariant.
- No WebClient change: the `creation` panel contract (cards carry exactly
  `key/display_name/race/race_description/subrace/emphasis/background` and SHALL NOT expose skills)
  is untouched.

## Capabilities

### New Capabilities

- `player-preset-skill-kits`: Preset template characters declare validated active/passive skill
  kits that activation grants; custom-created characters start with innate skills only. (Delta to
  the existing `player-character-creation` capability spec.)

## Key Decisions

- Skills are part of the immutable lore registry (frozen dataclass fields), validated at module
  load — the same load-time validation style as `SKILL_REGISTRY` itself.
- Elves remain the power-fantasy archetype: 悠花/悠奈/伊洛希雅 keep their story-defining
  multipliers (`body_enhancement_extreme`, mastery skills, 統御術) while stats stay inside the
  race's allocatable bands.
- Existing preset keys (`human_wanderer`, `foxkin_scout`, `elf_guardian`) are preserved so the
  existing command/browser/docs surface stays stable; new keys are appended in registry order.
