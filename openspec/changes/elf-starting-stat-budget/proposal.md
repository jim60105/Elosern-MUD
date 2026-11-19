# Proposal

## Why

The exact raw-stat budget forces custom elves to start with magic power between 462 and 537. A separate creation budget allows distinct physical and magical builds while preserving the species advantage.

## What Changes

- Give custom elves 75 points to spend exactly. A fully magical build starts at 200 magic power; a fully physical build starts at 100 and can maximize all three physical traits.
- Update WebClient and text creation to describe the same budget and conversion.
- **BREAKING:** Reset superseded pending custom-elf allocation drafts rather than interpreting old increments as new points. Do not change active characters, presets, companions, other races, lore ceilings or combat formulas.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `player-stat-allocation`: Define the distinct custom-elf allocation policy.
- `character-creation-ux`: Explain the selected profile's point units in text creation.
- `webclient-character-creation-ui`: Publish point and conversion bounds and resume stale allocations as incomplete.
- `generative-character-concept`: Validate suggested allocations against the same custom profile.

## Impact

Creation rules, draft staging, WebClient descriptor and controls, text wizard, concept validation, and creation tests. No world data rebalance. The design's “Human review: allocation briefing” section covers localized briefing and labels.
