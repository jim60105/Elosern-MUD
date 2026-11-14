# Proposal

## Why

The cost of a player action must not depend on the total world population (see `population-settlement-units` - Why). After `observed-unit-advance` a clock advance plans decisions and snapshots individuals only for the observed units, but each pass still enumerates every living monster of the world once to build its presence facts. That enumeration is a database query over every monster row plus one hit-point read per row, so the statement count of an action still grows with the world.

This work is mandatory. No measurement decides whether it happens.

## What Changes

- A scoped settlement pass enumerates only the individuals of its own units: the members of the scope's groups and the individuals registered on cells of the scope.
- The whole-world pass is unchanged.
- No game rule, draw, order, event or stored format changes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `population-settlement-units`: the database work of a clock advance does not depend on unobserved units.

## Impact

- Edits: `world/maps/regional_population.py`, `world/maps/population_lifecycle.py`.
- Tests: new `world/maps/tests/test_observed_unit_read_narrowing.py` (registered in `.github/evennia-shards.json`).
- Documentation: `docs/development/regional-monster-population.md`.
- Remaining whole-record work per pass, stated and not removed here: one decode and one store of the activity record, and one in-memory scan of the coordinate registration.

## Batch:

- depends-on: observed-unit-advance
- conflicts: serial chain, see `settlement-decode-reuse`.
- parallel with: `sqlite-wal-busy-timeout`.
