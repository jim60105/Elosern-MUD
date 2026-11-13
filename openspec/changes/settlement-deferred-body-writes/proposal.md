# Proposal

## Why

A profiled 3,580 second advance issued 152,666 `UPDATE typeclasses_attribute` statements and spent about 184 seconds in model `save` and 88 seconds pickling values for those writes. Most of them rewrite the same few rows many times inside one transaction: the population timeline once per moving body, the coordinate registration once per departure and arrival, the zone record once per boundary note, each body's reserve and posture once per posture segment, and each body's trait record twice per regenerated gauge. Only the last value of each row matters when the advance commits. `monster_activity.batched_state_writes` already applies this idea to the activity record alone.

## What Changes

- While a lifecycle settlement pass runs inside a clock advance, a write to the population timeline, the coordinate registration, the zone record, the site record, or a body's reserve or posture updates the value every reader sees at once, and is stored in the database once, when the pass completes.
- A body's gauge regeneration stores its trait record once per settlement call instead of twice per gauge.
- Writers of the timeline and the zone record hand their decoded value to the decode reuse of `settlement-decode-reuse`, so the next read does not decode what was just written.
- The field contact block stores everything pending before it starts and runs unbuffered.
- A failed pass stores nothing and puts every buffered value back to its pre-pass value in memory.
- Outside a clock advance nothing changes.
- No game rule, draw, order, event or stored format changes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `world-clock`: a lifecycle settlement pass inside an advance stores each written record once, with unchanged results and unchanged rollback.

## Impact

- Edits: `world/rules/surfaces.py`, `world/rules/fatigue.py`, `world/rules/clock.py` (`_settle_gauge_regen` only), `world/maps/population_lifecycle.py`, `world/maps/regional_population.py`, `world/maps/monster_activity.py`, `world/maps/monster_sites.py`.
- Tests: new `world/maps/tests/test_settlement_deferred_writes.py` (registered in `.github/evennia-shards.json`).
- Documentation: `docs/development/monster-field-behaviour.md`.
- Verification is by state equality and statement counts. No test measures wall-clock time.

## Batch:

- depends-on: settlement-outer-rollback
- conflicts: serial chain, see `settlement-decode-reuse`.
- parallel with: `sqlite-wal-busy-timeout`.
