## Why

The import path and the scene-builder NPC spawn path both run the lineage
auto-seed (`world/rules/progression.py::normalize_lineage_record`, composing
`lineage_ownership_closure` and `seed_lineage_proficiency`): they close a skill
set over its prerequisite chain and seed each unsatisfied edge to exactly its
required value, so a deeply authored entity arrives gate-usable rather than
merely owning a key it cannot use.

Preset activation does neither. It writes `preset.skill_lists()` verbatim and
hard-writes `skill_proficiency` as `{}`. An imported NPC and a preset player
holding the same skill keys are therefore not in the same state: the preset
player can own a tip skill whose `can_use_skill` predicate fails because no
prerequisite level was ever seeded. `yuka_darknight` and `elosia_shadowmoon`
both declare mastery-tier kits, so this is not hypothetical.

The registry also has no way to author a starting proficiency at all, which the
import card has had since `use-driven-skill-lineage`.

## What Changes

- `PlayerPreset` gains a keyword-only `skill_proficiency` field, a tuple of
  `(skill_key, xp)` pairs, defaulting to empty.
- A load-time validator rejects a key absent from `SKILL_REGISTRY`, a negative
  value, a non-numeric value, or a repeated key — matching the raw-record check
  the import validator already performs.
- Preset activation runs `lineage_ownership_closure()` over the declared active
  and passive keys and writes the closed lists, then `seed_lineage_proficiency()`
  over the closed set, with the preset's declared `skill_proficiency` entries
  overriding a seeded value exactly as an explicit import entry does.
- The declared keys keep their declared order; closure-added keys follow, so the
  existing ordering guarantee is preserved rather than reshuffled.
- Custom mode is unchanged: it grants no skills, so the closure is a no-op.

No backward compatibility or data migration: the project has no released users.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `player-character-creation`: the preset skill-kit requirement widens to cover
  the prerequisite closure and the seeded proficiency, plus the new registry
  field and its load-time validation.
- `skill-lineage`: the auto-seed requirement gains preset activation as a third
  caller of the shared helper, alongside the import loader and the scene
  builder.

## Impact

- `world/lore/player_presets.py` — the `skill_proficiency` field and its
  validator.
- `world/rules/character_creation.py` — the `skills` and `skill_proficiency`
  entries of the activation attribute map.
- `world/rules/progression.py` — read-only; the two existing public helpers are
  reused, not modified. `normalize_lineage_record` itself is not reused because
  it takes an import record dict, not a preset.
- `world/lore/tests/test_player_presets.py`,
  `world/rules/tests/test_character_creation.py`,
  `world/rules/tests/test_progression.py`.
- Unaffected: the import path, the scene builder, custom creation, and every
  WebClient payload schema (no preset card surface exposes the kit).
