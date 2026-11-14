# Proposal

## Why

Every `WorldClock.advance()` settles the whole monster population synchronously in one transaction. A profiled 3,580 second advance took 260 seconds, of which SQL was about 6%; the rest was Python that decodes the same stored records again and again: `from_pickle` 3.2 million calls, `regional_population._living_presence` 4,274 calls, `regional_population._protected_cells` 31,739 calls (reached through `monster_activity._destination_blocked`), plus a full scan of every monster and every player character behind each of them. None of these reads changes between two writes of the stored value.

This is the first of three changes that remove repeated work from settlement without changing any game result. It removes repeated decoding. `settlement-outer-rollback` removes repeated snapshots and savepoints; `settlement-deferred-body-writes` removes repeated body writes.

## What Changes

- The population timeline and the per-zone state record are decoded once per stored value: a read returns the earlier decode while the stored value object is the same object.
- Inside one lifecycle settlement pass, the list of living individuals, each individual's home zone and site marker, the active-session cell protection and the protected-cell set of one tick are computed once and reused until a write that can change them.
- Writes that can change them (a wave birth, a site populate, clear or recovery, a field contact block) drop the reused facts.
- A shared test projection of the complete population state is added, and a differential test proves that a pass with reuse and the same pass without reuse leave the same state under several interval partitions.
- No game rule, draw, order, event or stored format changes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `regional-population`: a settlement pass decodes each stored population record once per stored value and reuses pass-stable facts, with results equal to unshared reads.

## Impact

- Edits: `world/maps/regional_population.py`, `world/maps/population_lifecycle.py`, `world/maps/monster_sites.py`.
- Tests: new `world/maps/tests/_settlement_projection.py` (helper, no tests), new `world/maps/tests/test_settlement_decode_reuse.py` (registered in `.github/evennia-shards.json`).
- Documentation: `docs/development/regional-monster-population.md`.
- Verification is by state equality and by call counts. No test measures wall-clock time. A before/after timing of the profiling script is recorded in the hand-off as information only.

## Batch:

- depends-on: population-maintenance-log-tally
- conflicts: `world/maps/population_lifecycle.py` and `world/maps/regional_population.py` are edited by every later change of the settlement chain; the chain is strictly serial: `population-maintenance-log-tally` → `settlement-decode-reuse` → `settlement-outer-rollback` → `settlement-deferred-body-writes` → `population-settlement-units` → `unit-scoped-population-settlement` → `population-catch-up-entry-points` → `population-writer-guards` → `observed-unit-advance` → `observed-unit-read-narrowing` → `population-backlog-drain`.
- parallel with: `sqlite-wal-busy-timeout`.
