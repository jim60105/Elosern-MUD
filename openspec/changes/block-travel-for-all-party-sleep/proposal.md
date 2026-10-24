# Proposal

## Why

Actual movement preflight checks forced sleep only, while traversal prediction reconstructs awake posture from reserve. The user approved stationary parties for every sleep type, so voluntary sleepers must block real travel even when an awake companion is possessed or a flight cost waiver applies.

## What Changes

- **BREAKING**: broaden the original forced-only stationary requirement to every sleeping posture on every source-present effective party member.
- Enforce one authoritative early barrier across ordinary/interior connectors, settlement/grid, wilderness and both cross-layer gate directions, before pricing waivers or any writes.
- Retain actual posture in travel prediction; never infer awake state from positive/full reserve.
- Preserve lawful local actions and existing all-awake route pricing, follow and atomic settlement.
- Explicitly amend the approved design's forced-only wording and acceptance inventory during apply.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `party-system`: replace the forced-only stationary contract with all-sleep travel refusal.

## Impact

`world/rules/travel_cost.py`, actual movement/preflight consumers and gate/flight waiver entry points need focused boundary coverage. Update the existing requirement's traceability rather than adding a parallel contradictory capability. No carrying, sleeper teleport, split party, migration or live-save repair is authorized.

## Batch:

depends-on: none

worker: gpt-luna
branch: feat/block-travel-for-all-party-sleep
worktree: .worktrees/block-travel-for-all-party-sleep

Bounded workday unit: one policy correction propagated through existing travel consumers and focused tests. Runtime work is independent of `fix-body-sleep-lifecycle`; serialize shared fatigue/sleep design, manifests and traceability edits. `align-sleep-handoff-and-owner-dream` depends on this travel barrier for its end-to-end acceptance. Preserve unrelated `unify-map-glyphs-across-map-surfaces`; movement/map tests and shared manifest edits must be integrated serially if its touched paths overlap.
