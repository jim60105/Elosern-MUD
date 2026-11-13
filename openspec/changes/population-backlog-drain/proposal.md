# Proposal

## Why

After `observed-unit-advance`, a clock advance settles only the observed population units, so the cost of a player action no longer depends on the total world population. Units nobody observes fall behind. Their debt is paid in one step when a player first comes near, and that step grows with the game time the unit was left alone: a zone left for thirty game days would freeze the action that enters it.

The debt must be paid off the action path, in small pieces, while the player is reading or idle. Because any partition of the same elapsed interval gives the same result per unit, paying it in pieces at arbitrary real times changes no outcome.

This work is mandatory. No measurement decides whether it happens.

## What Changes

- A drain operation picks the closed set of units that is furthest behind and settles it forward by at most one bounded slice of game time, in its own short transaction with full rollback. It never advances the world clock and admits no field contact.
- A global script calls the drain at a configured real-time interval. Three settings control it: enabled, interval in real seconds, slice in game seconds; each has an environment override.
- One info event is emitted per drain run that settled something. A run with nothing to do is silent.
- A drain failure is reported as an error event and leaves the world as it was. The same run then tries the next most lagging set, so one bad unit does not starve the others.
- The main design document's clock section is amended: materialising already elapsed game time in the background is not world time passing.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `population-settlement-units`: lagging units are settled forward in bounded background slices.

## Impact

- New `world/maps/population_drain.py`; edits to `world/maps/population_units.py` (lagging-set query), `server/conf/settings.py`, `server/conf/test_settings.py`, `.env.example`.
- Tests: new `world/maps/tests/test_population_drain.py` (registered in `.github/evennia-shards.json`); the environment-override inventory tests under `server/conf/tests/test_env_overrides/` cover the three new names.
- Documentation: `docs/development/settings-and-environment.md`, `docs/development/regional-monster-population.md`, event catalog §4.2 of `docs/superpowers/specs/2026-09-02-observability-logging-design.md`, amendment in `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` §6.5.
- The Server reactor runs one short settlement transaction per interval while a backlog exists.

## Batch:

- depends-on: observed-unit-read-narrowing
- conflicts: serial chain, see `settlement-decode-reuse`. `server/conf/settings.py` and `server/conf/test_settings.py` are also edited by `sqlite-wal-busy-timeout` in a different section; keep both edits.
- parallel with: `sqlite-wal-busy-timeout`.
