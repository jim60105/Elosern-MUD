## Why

The magic-level cast gate today treats every element identically: a single
global `magic_level` number gates all eight elements against the same tier
thresholds, so a caster with a narrative "擅長屬性" has no mechanical
expression, and a human can never reach 主宰-tier magic at all (cap 90 vs.
threshold 91). Subraces already declare `affinity_elements` for elves, but no
rule consumes it. We want each caster's element affinities to control how
fast they unlock each element's tiers — favored elements unlock earlier,
non-favored elements later — while keeping exactly one growing `magic_level`
counter and leaving the XP/growth system untouched.

## What Changes

- New pure derivation `element_affinity_multiplier(entity, element)`:
  1.1 for a declared affinity element, 0.9 for a non-affinity element on an
  entity that declares affinities, and exactly 1.0 for an entity with no
  declared affinities (current behavior preserved).
- `can_cast_spell_tier` gates on `floor(magic_level × multiplier)` instead of
  the raw `magic_level`; mastery override and the fixed threshold table are
  unchanged. This lets a human reach 主宰 (unlocked at level 83) for favored
  elements while non-favored elements stay capped at 賢者.
- New per-entity attribute `entity.db.affinity_elements` (validated element
  keys). Sources: player presets declare it, custom creation collects it with
  **race-bounded counts** (human ≤ 2, beastfolk ≤ 1, elf derived from the
  chosen subrace, not player-chosen), and character imports carry it. For
  elves the subrace is the **sole affinity authority in every channel**:
  explicit elf-supplied affinity is rejected (custom and import) or must be
  empty (preset load validation), and the elf's set is always the subrace
  seed. Import is bounded to 8 unique lore element keys structurally, with
  race-aware semantic counts (human ≤ 2, beastfolk ≤ 1, elf none).
- Balance constants move into `progression.yaml`.

## Capabilities

### New Capabilities
- `element-affinity`: per-entity element affinity data, the multiplicative
  derivation, and its consumption by the magic cast gate.

### Modified Capabilities
- `element-mastery`: `can_cast_spell_tier` compares an element-effective magic
  level (affinity-scaled) instead of the raw counter; mastery override and the
  threshold table are unchanged.
- `player-character-creation`: custom mode collects a race-bounded affinity
  element choice (human 0–2, beastfolk 0–1, elf from subrace seed), persisted
  at activation.
- `import-schema`: optional `affinity_elements` array (up to 8 unique lore
  element keys; an elf record supplying a set is rejected semantically since
  the elf's set is subrace-derived).
- `import-validation`: validates `affinity_elements` (unknown key, duplicate,
  or race-bound violation — human ≤ 2, beastfolk ≤ 1, elf none — rejected).
- `webclient-character-creation-ui`: the custom form exposes the affinity
  element picker with race-dependent bounds.

## Impact

- `world/rules/progression.py`: `element_affinity_multiplier`, amended
  `can_cast_spell_tier`; `world/rules/rulebook/progression.yaml` gains the two
  multiplier constants.
- `world/lore/player_presets.py`: `PlayerPreset.affinity_elements` + values +
  validation.
- `world/rules/character_creation.py` (+ `creation_wizard.py`,
  `commands/character_creation.py`): custom affinity input, race-bounded
  validation, subrace seeding for elves, attribute write at activation.
- `world/imports/{schema,validate,loader}.py`: optional `affinity_elements`.
- WebClient custom creation form + its backend view.
- Specs amended: `element-mastery`, `player-character-creation`,
  `import-schema`, `import-validation`, `webclient-character-creation-ui`;
  `2026-08-12-skill-system-redesign-design.md` §4.2 (D4) amended for the
  element-effective gate.
- No change to XP accumulation, `magic_rank_title`, combat
  `effective_value("magic_level")`, or mastery override. `ActionResolver` and
  `monster_behaviour` consume the amended gate unchanged.
