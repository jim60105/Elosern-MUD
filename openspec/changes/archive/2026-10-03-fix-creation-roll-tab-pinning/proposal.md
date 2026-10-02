## Why

Clicking the name-roll button on the character-creation overlay's custom tab jumps the wizard back to the preset tab. The concept flow already pins its tab during an admitted request, but the same stage-mirror race remains unguarded for name rolls.

## What Changes

- Extend the existing stage-mirror in-flight pin to cover the admitted name-roll loading state, preserving the custom tab through dispatch publication, result settlement, and gate release.
- Generalize the creation UI's tab-pinning clause from concept-only loading to the creation form's own in-flight loading state, and add a name-roll scenario while retaining the concept scenario.
- Add a real-store Vitest regression using AppClient and a fake transport to prove both tab stability and matching-request name backfill.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-character-creation-ui`: The custom tab remains presented throughout an admitted name roll and its settlement instead of being reset by unchanged-stage republishes.

## Impact

Implementation is limited to the overlay's composable wiring, the existing stage watcher pin condition/comments, and a real-store overlay regression beside the existing concept-navigation tests. This is a small frontend fix, well under one engineer-day, with no backend, protocol, persistent-state, or player-command surface changes. `creation.roll_name` remains result-only; command docs and `.github/evennia-shards.json` stay unchanged. No compatibility layer or migration is needed.
