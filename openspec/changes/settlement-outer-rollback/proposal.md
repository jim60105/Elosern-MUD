# Proposal

## Why

`WorldClock.advance()` already builds one pre-advance snapshot registry for every surface the population lifecycle may write, runs every stage in one `transaction.atomic()`, and restores the registry when anything raises. Inside that advance each single operation protects itself a second time: `monster_activity._commit_stay` and `_commit_departure`, `fatigue.settle_fatigue_intervals`, `regional_population.commit_population_wave` and `monster_sites.settle_site_recovery` each take their own attribute snapshot and open their own savepoint. A profiled 3,580 second advance issued 194,410 savepoint pairs and 71,925 attribute snapshots (about 93 seconds, most of it `copy.deepcopy` and `from_pickle`) for protection the advance already provides.

## What Changes

- While a lifecycle settlement pass runs inside a clock advance, the five operations above take no snapshot of their own and open no savepoint of their own. A failure propagates to the advance, which rolls back and restores everything, as it does today for a failure in a later stage.
- The same operations called outside a clock advance (combat, GM console, direct owner calls, tests) keep their own snapshot and savepoint unchanged.
- The field contact block inside a pass keeps full inner protection: a failed contact still restores its participants and the advance still continues.
- No game rule, draw, order, event or stored format changes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `world-clock`: lifecycle operations inside an advance rely on the advance's rollback and add no savepoint or snapshot of their own, with unchanged results and unchanged recovery.

## Impact

- Edits: `world/rules/surfaces.py`, `world/rules/clock.py`, `world/rules/fatigue.py`, `world/maps/population_lifecycle.py`, `world/maps/monster_activity.py`, `world/maps/regional_population.py`, `world/maps/monster_sites.py`.
- Tests: new `world/maps/tests/test_settlement_outer_rollback.py` (registered in `.github/evennia-shards.json`).
- Documentation: `docs/development/monster-field-behaviour.md`.
- The advance's own up-front registry (one snapshot of every tracked individual per advance) is unchanged here; `observed-unit-advance` narrows it.

## Batch:

- depends-on: settlement-decode-reuse
- conflicts: serial chain, see `settlement-decode-reuse`. Shares `monster_activity._commit_stay`, `_commit_departure` and `fatigue.settle_fatigue_intervals` with `population-maintenance-log-tally` (already merged through the chain) and with `settlement-deferred-body-writes` (next).
- parallel with: `sqlite-wal-busy-timeout`.
