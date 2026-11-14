# Proposal

## Why

The cost of a player action must not depend on the total world population (see `population-settlement-units` - Why). `population-catch-up-entry-points` makes every known entry point catch up the units it touches. An entry point that was missed, or one added later, would write population state into a unit that is behind the world tick and silently corrupt its history once the clock stage stops settling the whole world (`observed-unit-advance`).

This change makes that impossible: population writers refuse a lagging unit by name. It also lets an operator see how far a monster's unit has been settled. It merges while every unit is still always current, so it refuses nothing in practice when it lands.

This work is mandatory. No measurement decides whether it happens.

## What Changes

- Outside a running settlement pass, registering an explicit group, creating a group, recording a presence transition, recording a cell protection and committing a monster departure refuse, with a named error and no write, when a unit they touch is behind the current world tick.
- The GM monster view shows the settlement progress of the monster's unit and marks a unit that is behind. The view never settles anything.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `population-settlement-units`: the refusal of writes into a lagging unit and the GM progress read.

## Impact

- Edits: `world/maps/population_units.py`, `world/maps/regional_population.py`, `world/maps/monster_activity.py`, `web/gm/readers/monsters.py`.
- Tests: new `world/maps/tests/test_population_writer_guards.py` (registered in `.github/evennia-shards.json`); one addition to the GM reader label test in `world/maps/tests/test_monster_activity.py`.
- Documentation: `docs/development/regional-monster-population.md`.

## Batch:

- depends-on: population-catch-up-entry-points
- conflicts: serial chain, see `settlement-decode-reuse`.
- parallel with: `sqlite-wal-busy-timeout`.
