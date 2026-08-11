## Why

Combat settlement writes round effects, session metadata, exam terminal state, the world tick, and session clearing in separate durable commits (audit finding F05). A process termination between them leaves half-round durable state, double-counts hostile combat time on restart, or permanently loses exam time. (Startup restore ordering versus wilderness reconciliation is a separate change: `fix-startup-session-restore-order`.)

## What Changes

- Add a durable `settled_tick` marker to the session record so a terminal outcome is settled exactly once, even when a restart re-reads the session.
- Wrap the round's action effects, session metadata update, and terminal settlement (exam outcome, clock advance, session clearing) in one outer transaction with snapshot/restore of all touched entities.
- Session restoration skips already-settled sessions.

## Capabilities

### Modified Capabilities

- `player-combat-session`: round-and-settlement atomicity and restart idempotency.

## Impact

- `world/rules/combat_session.py` (record, `submit_player_action`, `settle_session`, `restore_active_session`), `world/rules/guild_exams.py` (exam settlement ordering inside the transaction), `world/rules/action.py` snapshot dispatch reuse; companion startup-order work lives in `fix-startup-session-restore-order`.
