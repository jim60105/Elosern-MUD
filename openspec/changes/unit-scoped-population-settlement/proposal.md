# Proposal

## Why

The cost of a player action must not depend on the total world population (see `population-settlement-units` - Why). `population-settlement-units` defined independent settlement units and their cursors. The lifecycle coordinator and the three owners (`monster_activity`, `regional_population`, `monster_sites`) can still only settle the whole world at once.

This change lets the coordinator settle one closed set of units from its own cursor to a target tick, and proves that settling units separately, in any order and under any partition of time, gives the same world as settling everything together. It changes no behaviour yet: the clock stage still settles the whole world. `observed-unit-advance` switches the stage over.

This work is mandatory. No measurement decides whether it happens.

## What Changes

- A settlement scope names a closed set of units and the groups, zones and sites inside it.
- Every owner step of a lifecycle pass accepts a scope and then considers only the groups, journeys, zones, sites, protection and timeline evidence of that scope.
- The coordinator gains a scoped pass that starts at the scope's cursor, settles to a target tick and advances only that scope's cursors.
- Timeline evidence is retired only when every unit it concerns has been settled past it.
- A scoped pass refuses, by a named error, to place an individual on a cell outside its scope, and refuses a scope whose units have different cursors.
- The whole-world pass is unchanged and remains the clock stage.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `population-settlement-units`: a closed set of units can be settled alone, with results equal to whole-world settlement.

## Impact

- Edits: `world/maps/population_units.py`, `world/maps/population_lifecycle.py`, `world/maps/monster_activity.py`, `world/maps/regional_population.py`, `world/maps/monster_sites.py`.
- Tests: new `world/maps/tests/test_scoped_population_settlement.py` (registered in `.github/evennia-shards.json`).
- Documentation: `docs/development/regional-monster-population.md`.
- No stored format change.

## Batch:

- depends-on: population-settlement-units
- conflicts: serial chain, see `settlement-decode-reuse`.
- parallel with: `sqlite-wal-busy-timeout`.
