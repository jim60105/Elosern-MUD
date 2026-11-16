# Proposal

## Why

One background drain run settles one closed set of units by one slice of game time and then waits for the next repeat. The live log showed `units=1 ... remaining=217` on every run: with 218 units and one unit-slice per repeat, the backlog only grows while a player plays, and it shrinks very slowly when nobody does.

Each run also repeats work it could share. `lagging_sets`, the drain's `build_scope` and the pass's own `build_scope` each compute the units of every group of the world (`population_units.group_units_map`), although the activity record did not change between them.

After `population-drain-idle-gate` a run only starts when no player has sent input recently, so one run can pay more than one unit-slice.

## What Changes

- One drain run performs up to a configured number of settlement steps (new setting `POPULATION_DRAIN_STEPS_PER_RUN`, default 4, positive integer, environment override of the same name). Each step is exactly what one run was before: the most lagging closed set, one slice, its own transaction, full rollback, one event.
- After a step the run picks the most lagging set again from its updated cursors, so a far-behind set can take several steps of one run, and several sets can each take one.
- A set whose step fails is not tried again in the same run. The run stops after three failed sets (the present bound).
- `drain_population_backlog(slice_seconds, max_steps=1)` returns the number of steps that settled (an `int`; `0` when nothing settled).
- The units of every group are computed once per unchanged activity record, unit index and published geography, and shared by every lagging-set, closure and scope query.
- No settlement outcome changes: any partition of the same elapsed interval gives the same per-unit result, and each step is an unchanged scoped pass.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `population-settlement-units`: a drain run performs a bounded number of steps; group units are computed once per activity record.

## Impact

- Code: `world/maps/population_drain.py`, `world/maps/population_units.py` (`group_units_map`), `server/conf/settings.py`, `server/conf/test_settings.py`, `.env.example`.
- Tests: `world/maps/tests/test_population_drain.py`, `world/maps/tests/test_population_units.py`, `server/conf/tests/test_env_overrides/_support.py`.
- Documentation: `docs/development/regional-monster-population.md` (drain section), `docs/development/settings-and-environment.md`, event catalog §4.2 of `docs/superpowers/specs/2026-09-02-observability-logging-design.md`.
- The reactor is blocked for up to `POPULATION_DRAIN_STEPS_PER_RUN` steps per repeat instead of one.
- Human-reviewed: none. Every behaviour of this change is established by tests. Whether the default of 4 steps suits the live world is a tuning decision recorded as a non-blocking observation in `tasks.md`.

## Batch:

- depends-on: population-drain-idle-gate
- depends-on: population-snapshot-part-scoping
- This change requires commit `c0736d44` (`fix/population-group-units-memo`) to be merged to `master` first: it edits `population_units.group_units_map` beside that commit's `_area_units` memo and `warm_group_units`.
- conflicts: `population-drain-idle-gate` edits `PopulationDrainScript.at_repeat` and the settings inventories; this change edits the same places and is ordered after it. The dependency on `population-snapshot-part-scoping` is an ordering one: both edit `docs/development/regional-monster-population.md`, and the default of 4 steps assumes the cheaper step that `monster-activity-record-parts` and `population-snapshot-part-scoping` deliver.
- parallel with: none.
