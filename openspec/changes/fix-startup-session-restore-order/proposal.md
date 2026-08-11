## Why

Startup runs wilderness population reconciliation before persisted combat-session restoration, so a defeated population monster is deleted and respawned before the session restore reads it — converting a committed victory into a defeat after a restart (audit finding F10).

## What Changes

- Persisted combat sessions are restored before any wilderness population reconciliation runs in the deterministic startup sequence.
- As defense in depth, population reconciliation skips any monster referenced by a persisted `active_combat` record until that session is settled.
- No change to the reconciliation's behavior for monsters no session references.

## Capabilities

### Modified Capabilities

- `wilderness-monster-population`: active-session participants are exempt from reconciliation until settled.
- `player-combat-session`: startup restores sessions before population reconciliation.

## Impact

- `server/conf/at_server_startstop.py` (startup order), `world/maps/wilderness_population.py` (participant guard), restart-focused tests; independent from the settlement-atomicity work in `fix-combat-settlement-recovery` (which this change can land before or after).
