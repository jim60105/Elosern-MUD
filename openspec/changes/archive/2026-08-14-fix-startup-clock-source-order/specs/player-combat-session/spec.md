## ADDED Requirements

### Requirement: Startup combat restoration advances time only after every deterministic clock source is registered

The deterministic startup sequence SHALL run every deterministic sync that precedes session restoration — `sync_service_interiors()`, `sync_quest_runtime()`, `sync_guild_economy()`, `sync_guard_npc()`, and `sync_npc_schedules()` — before `restore_persisted_sessions()` may advance the world clock, so the recovery advance's `WorldClock.advance` runs the same registered stage set as any ordinary advance (`quest_deadlines`, `caravan_arrivals`, `shop_hours`, `npc_schedules`, plus `instance_reclamation` registered by `sync_grid`). The sequence SHALL still run `restore_persisted_sessions()` before `sync_wilderness()` so a defeated population monster referenced by a committed session is never deleted or respawned first. No recovery window can bypass an unregistered deterministic callback.

#### Scenario: All deterministic syncs precede session restoration, which precedes wilderness sync

- **WHEN** the `at_server_start()` call sequence is observed
- **THEN** `sync_service_interiors()`, `sync_quest_runtime()`, `sync_guild_economy()`, `sync_guard_npc()`, and `sync_npc_schedules()` all run strictly before `restore_persisted_sessions()`, which runs strictly before `sync_wilderness()`

#### Scenario: A due quest deadline inside a recovery window fails

- **WHEN** a cold start begins with an active quest whose `deadline_tick` falls inside the settlement window of a recovered invalid session
- **THEN** the quest record transitions to `FAILED` with reason `deadline_expired` during restoration, because `quest_deadlines` was already registered
