# Proposal

## Why

Elf presets still spend a raw budget of 437 points, so their starting magic power cannot fit the custom elf range of 100 to 200.

## What Changes

- Apply the existing custom elf allocation policy to elf presets and reauthor their allocations.
- Apply those same base values when a preset is used to build a new starting companion.
- Keep non-elf allocations, active characters, combat rules and the species lore ceiling unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `player-stat-allocation`: Share the race-specific policy between custom and preset creation.
- `preset-authoring-docs`: Document the shared policy and the difference between point caps and stat spans.

## Impact

Starting policy, four elf cards, preset activation and companion construction through their shared resolver, focused tests, and authoring documentation.
