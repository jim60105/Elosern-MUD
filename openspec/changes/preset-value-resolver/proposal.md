## Why

`preflight_character_creation` computes a preset's final trait values inline:
it resolves the race/subrace bounds through `resolve_starting_profile()`, adds
the preset's allocations, applies the subrace static modifiers, and pins
`guild_merit`. That computation is the definition of "what this card is worth",
and right now it exists only inside a function that also validates account
ownership, names, ages, registry membership, affinity sets, and sex.

`preset-companion-model` needs the same numbers to build an NPC from a preset
card, and a companion whose stats silently drift from the player version of the
same character would be a hard bug to see. Reaching into the preflight function
is not an option — it requires an account and a pending character shell.

Extracting the computation on its own, with the existing creation tests as the
regression net, keeps that refactor out of the companion change where a
behavior difference would be much harder to attribute.

## What Changes

- A pure `resolve_preset_values(preset)` is extracted from
  `preflight_character_creation` into `world/rules/character_creation.py`'s
  module surface: no account, no character, no writes, no validation beyond what
  the registry already guarantees at load.
- `preflight_character_creation` calls it, so the player path is byte-identical.
  The existing creation tests are the regression net and MUST pass unedited.
- Nothing else changes. No new consumer is added in this change; the companion
  builder is the first, in `preset-companion-model`.

No backward compatibility or data migration: the project has no released users.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `player-stat-allocation`: the starting-profile requirement gains the statement
  that one shared pure resolver owns the bounds-plus-allocation-plus-modifier
  computation, so every consumer of a preset's values derives them identically.

## Impact

- `world/rules/character_creation.py` — one function extracted; no behavior
  change.
- `world/rules/tests/test_character_creation.py` — a test pinning that the
  resolver's output equals what activation persists for each shipped preset.
- Unaffected: every caller of `preflight_character_creation`, custom creation,
  the WebClient actions, and the import path.
