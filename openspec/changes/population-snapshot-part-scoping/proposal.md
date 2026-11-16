# Proposal

## Why

Before a scoped settlement writes anything (a clock advance over the observed units, a synchronous catch-up, a background drain run), `population_lifecycle.snapshot_population_lifecycle_surfaces` copies the surfaces the pass may write, so a failure can restore memory after the database rolls back. The activity record enters that copy whole, twice: once through `regional_population.snapshot_population_surfaces` and once through `monster_activity.snapshot_activity_surfaces`. Each copy unpickles every group of the world, although a scoped pass can only write the groups of its own closed set of units.

After `monster-activity-record-parts` the record is stored in one part per settlement unit, so the copy can name exactly the parts a scope may write.

## What Changes

- The rollback registry of a scoped settlement holds the activity header, the parts of the scope's units and the parts that hold the scope's groups. It holds no part of any other unit.
- A unit of the scope that has no stored part yet is named as absent, so a part created by a failed pass is removed by the restore.
- When the scope holds the residual unit, the registry also holds every part that stores a receipt whose group no longer exists, because only a residual scope may retire such a receipt.
- The activity parts are copied once per registry, not twice.
- Every other caller of the activity and population snapshot functions (single-group operations, registration, bootstrap, GM tools, movement settlement) keeps the whole-record snapshot it has today.
- No settlement outcome, no stored format and no restore function changes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `population-settlement-units`: a scoped settlement snapshots only the activity parts its scope may write.

## Impact

- Code: `world/maps/monster_activity.py` (`activity_record_surfaces`, new `scope_part_units`, `snapshot_activity_surfaces`, `snapshot_monster_activity_surfaces`), `world/maps/regional_population.py` (`snapshot_population_surfaces`, `snapshot_regional_population_surfaces`), `world/maps/population_lifecycle.py` (`snapshot_population_lifecycle_surfaces`).
- Tests: new `world/maps/tests/test_population_snapshot_scope.py` (registered in `.github/evennia-shards.json`).
- Documentation: `docs/development/regional-monster-population.md` (section "Activity record storage" added by `monster-activity-record-parts`).
- Human-reviewed: none. Every behaviour of this change is established by tests.

## Batch:

- depends-on: monster-activity-record-parts
- This change does not require commit `c0736d44` (`fix/population-group-units-memo`).
- conflicts: edits the snapshot functions `monster-activity-record-parts` introduces; it is ordered directly after that change. `population-drain-batched-runs` edits `docs/development/regional-monster-population.md` in a different section and is ordered after this change.
- parallel with: `population-drain-idle-gate` (no shared file).
