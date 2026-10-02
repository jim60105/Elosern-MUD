## Why

P2-1: shipped host and examiner cards describe adults with long careers, while creation/synchronization supplies canonical ages of 18. Mechanical identity and authored characterization must agree on fresh development worlds.

## What Changes

- Author explicit canonical age/apparent-age pairs for every shipped host and examiner profile and consume them before generic defaults in the existing creation flows.
- Preserve independent set-if-absent age semantics, service reuse, player-edited cards, and the inclusive 0..10000 age bounds.
- Correct only contradictory host timeline/appearance claims; inventory all 25 hosts and seven examiners.
- No companion changes, data migration, in-place cutover, bundle integration, or LLM feature.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `npc-profile-registry`: explicit bounded authored profile ages and complete host/examiner inventory.
- `npc-canonical-age`: prefer explicit authored ages while preserving independent set-if-absent fallback.
- `place-driven-service-sync`: authored age initialization without overwriting reused instances.
- `guild-rank-exams`: examiner-specific canonical ages instead of the old default-18 requirement.

## Impact

One engineer-day: profile vocabulary and six shipped slices, `typeclasses/npcs.py` age helper, host/examiner producers, focused synthetic lifecycle tests and roster contract review. No transport schema or age editor changes. Existing development databases remain unsupported; use the existing reset runbook (§13b), not repair code. Companion presets and official prose remain single-source and unchanged (§13a).

## Batch:

depends-on: none

Code-conflict notes: `typeclasses/npcs.py` is shared with `npc-offline-greeting-literal-output` (different functions; sequence commits). Existing lifecycle/roster test modules and shard registration may overlap mechanically. Profile slices and producers are otherwise exclusive to this change. No semantic dependency on the other three fixes.
