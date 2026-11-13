# Proposal

## Why

The cost of a player action must not depend on the total world population (see `population-settlement-units` - Why). After `unit-scoped-population-settlement` a closed set of units can be settled alone. Before the clock stage may stop settling the whole world (`observed-unit-advance`), every place that reads or writes population state for a decision must be sure the units it touches are settled to the current tick, and must fail loudly when they are not.

This change adds that safety net while every unit is still always current, so it is a no-op in practice when it merges. It makes the next change safe to merge.

This work is mandatory. No measurement decides whether it happens.

## What Changes

- A catch-up operation settles the closed set of units around given cells from its cursor to the current tick, in its own transaction with full rollback, and emits one info event when it did work.
- The set of observed units is defined: the residual unit, the units within ground sight of every player character, and the units around locations an action announced it is about to enter.
- Every command starts by catching up the observed units. A movement edge announces and catches up its destination before it is settled. Quest materialisation, the GM placement and removal verbs and the quest site-target read catch up their target cell first.
- Population writers refuse a cell whose unit is behind the current tick, with a named error and no write.
- The GM monster view shows the settlement progress of the monster's unit and marks a unit that is behind. GM views never catch up.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `population-settlement-units`: catch-up, observed units, the refusal of writes into a lagging unit, and the GM progress read.

## Impact

- Edits: `world/maps/population_units.py`, `world/maps/population_lifecycle.py`, `world/rules/clock.py`, `world/maps/regional_population.py`, `world/maps/monster_activity.py`, `world/maps/gm.py`, `world/quests/materializer.py`, `world/quests/runtime.py`, `world/rules/movement_settlement.py`, `commands/command.py`, `web/gm/readers/monsters.py`.
- Tests: new `world/maps/tests/test_population_catch_up.py` (registered in `.github/evennia-shards.json`); one addition to the GM reader test that already asserts `placement_section` labels.
- Documentation: `docs/development/regional-monster-population.md`, the event catalog §4.2 of `docs/superpowers/specs/2026-09-02-observability-logging-design.md`.
- No command is added, removed or renamed; `docs/game/commands.md` is unaffected.

## Batch:

- depends-on: unit-scoped-population-settlement
- conflicts: serial chain, see `settlement-decode-reuse`.
- parallel with: `sqlite-wal-busy-timeout`.
