# Proposal

## Why

One committed clock advance (`tick_from=50 tick_to=3630`) wrote about 14,500 info lines: `fatigue_transition` 7,722, `monster_departed` 3,471, `monster_activity_decided` 2,421, `monster_arrived` 2,228. It rotated four 1 MB `server.log` files and buried the player's own events. These lines describe unobserved world maintenance, one line per body or group.

## What Changes

- Inside the population lifecycle settlement of a clock advance, the per-entity events `fatigue_transition`, `monster_activity_decided`, `monster_departed`, `monster_arrived` and `monster_arrival_deferred` are emitted at debug level and counted.
- Each lifecycle settlement pass that counted at least one such event emits one info event `population_maintenance_settled` on durable commit, carrying the tick range and one count per event name.
- The same events stay at info level everywhere else: a monster escape in combat, a direct owner operation, the acting party's own fatigue transitions, and everything a field contact admission writes.
- All other events keep their level: `clock_advance`, `monster_population_wave`, `monster_population_recovery_blocked`, every `monster_site_*` event, `monster_escape_resolved`, `field_contact_*`.
- The event catalog in `docs/superpowers/specs/2026-09-02-observability-logging-design.md` §4.2 and the event tables in `docs/development/monster-field-behaviour.md` record the new event and the level rule. `docs/superpowers/specs/2026-11-03-monster-field-behaviour-and-escape-design.md` §11 gets a dated amendment note.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `observability-logging`: world-maintenance settlement reports one aggregated boundary event per pass instead of one info event per entity.

## Impact

- New `world/observability/tally.py`; edits to `world/maps/population_lifecycle.py`, `world/maps/monster_activity.py`, `world/rules/fatigue.py`.
- Tests: new `world/observability/tests/test_tally.py` and `world/maps/tests/test_population_maintenance_log.py` (both registered in `.github/evennia-shards.json`); existing event assertions in `world/maps/tests/test_monster_activity.py`, `world/rules/tests/test_fatigue.py` and `world/rules/tests/test_world_escape.py` are re-run and adjusted only where they assert an info call for an event that the lifecycle pass now counts.
- No change to game state, to returned `ScheduledEvent` lists, or to the facade's four functions.

## Batch:

- depends-on: none
- conflicts: `settlement-outer-rollback` and `settlement-deferred-body-writes` edit the same functions (`monster_activity._commit_stay`, `_commit_departure`, `_arrive`, `_settle_due_journeys`, `fatigue.settle_fatigue_intervals`) and `population_lifecycle.settle_population_lifecycle`. This change lands first; `settlement-decode-reuse` declares the dependency so the settlement chain starts after it.
- parallel with: `sqlite-wal-busy-timeout`.
