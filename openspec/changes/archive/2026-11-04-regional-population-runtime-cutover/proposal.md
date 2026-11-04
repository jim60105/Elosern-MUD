# Proposal

## Why

The prepared population and consumer contracts must replace the live coordinate-bound ambient path completely. Keeping room-entry refill or tier examples would defeat delayed sparse regional recovery.

## What Changes

- **BREAKING** Activate the regional owner once on fresh-world provisioning, register recovery before any restoring clock advance and make room preparation attach existing individuals only.
- Remove tier-example, capital hunting-band, immediate per-cell refill, coordinate-slot identity and all obsolete callers/contracts/exports/tests.
- Integrate current bounded approved-species pools, manual exceptions, actual-live views, offline quests and whole-cell combat with real smoke, failure and reload evidence.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `wilderness-monster-population`: Revise the behavior contract in this change's delta.
- `player-combat-session`: Revise the behavior contract in this change's delta.

## Impact

`ElosernWildernessMapProvider.at_prepare_room` still calls ensure_population on every activation. `sync_wilderness` re-prepares active rooms on restart. The old population module owns tier-example, capital-band, coordinate-hash slots, cleanup and prospective projection. Startup currently restores sessions before wilderness sync; new clock source registration must precede restoration without restoring visit-driven births.

Planning only for `docs/superpowers/specs/2026-11-03-regional-monster-population-design.md`, under the 2026-07-29 architecture. Offline deterministic single-writer ownership is retained. No implementation, apply, archive, migration or main-spec edit occurs in this proposal commit. Human judgments of ecology, tutorial wording and presentation truthfulness are reviewed in `docs/development/regional-monster-population.md` during implementation; tests establish mechanisms rather than shipped wording or balance values.

## Batch:

depends-on: whole-cell-field-engagement
depends-on: regional-population-recovery
depends-on: manual-monster-compositions
depends-on: regional-hunt-supply-cutover
depends-on: actual-live-population-view

Code conflicts:
- All prerequisites share final consumer expectations; land this integration after their code and deltas.
- monster_placement.py, wilderness_population.py, maps bootstrap/runtime/geography and server startup are exclusive to this cutover while it lands.
- All test/shard/docs edits serialize; there are no other active changes in the inspected CLI state.

The complete 15-item disposition and batch conflict/dependency matrix are in design.md. Movement, aggression, escape relocation and new monster content remain explicitly deferred integration boundaries.
