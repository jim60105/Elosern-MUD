# Proposal

## Why

Every clock advance settles the monster population of the whole world, so the cost of one player action grows with the world-wide monster count. The changes `settlement-decode-reuse`, `settlement-outer-rollback` and `settlement-deferred-body-writes` make each settled boundary cheaper, but the cost still grows as the world grows, and the problem returns. The cost of a player action must not depend on the total world population.

The remedy is to settle, during an action, only the part of the world the acting party can observe or touch, and to settle the rest later. That is only correct when the world can be divided into parts whose settlement never reads each other's state. This change defines those parts (settlement units) and records, per unit, how far it has been settled. It changes no behaviour: every unit is still settled by every advance. The next changes (`unit-scoped-population-settlement`, `population-catch-up-entry-points`, `observed-unit-advance`, `population-backlog-drain`) use it.

This work is mandatory. No measurement decides whether it happens.

## What Changes

- A pure resolver divides the authored ecology zones and region-bound activity areas into settlement units: two of them are in one unit when their rectangles in the same region overlap. Everything else (rooms, cells in no zone and no area) belongs to one residual unit.
- A pure function gives the set of units one live group touches (its home, position, journey endpoints, activity area and owning zone or site), and another gives the closure of a set of units over the groups and sites that link units.
- The wilderness stores one settled-through tick per unit. Fresh provisioning creates the record; server start creates it for a provisioned world that lacks it, from the world's current settlement progress.
- The lifecycle pass records the pass endpoint for every unit. Nothing reads the record for decisions yet.

## Capabilities

### New Capabilities

- `population-settlement-units`: the division of the monster population into independently settleable units, and each unit's settlement progress.

### Modified Capabilities

None.

## Impact

- New `world/maps/population_units.py`; edits to `world/maps/regional_population.py` (`initialize_population_seed`, the snapshot of population surfaces), `world/maps/population_lifecycle.py`, `world/maps/bootstrap.py` or the startup step that provisions the population (design D5 names how to find it).
- Tests: new `world/maps/tests/test_population_units.py` (registered in `.github/evennia-shards.json`).
- Documentation: `docs/development/regional-monster-population.md`.
- One new wilderness attribute, `population_unit_cursors`. No migration: the startup step is idempotent provisioning.

## Batch:

- depends-on: settlement-deferred-body-writes
- conflicts: serial chain, see `settlement-decode-reuse`.
- parallel with: `sqlite-wal-busy-timeout`.
