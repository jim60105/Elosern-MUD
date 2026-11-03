# Spec Delta

## MODIFIED Requirements

### Requirement: Startup restores combat sessions before wilderness population initialization
Startup SHALL register population clock sources before restoring combat sessions and restore recorded sessions before fresh wilderness population initialization, protecting recorded individuals throughout.

#### Scenario: Defeated population monster survives until session restore
- **WHEN** a restart follows a terminal round against a wilderness population monster whose session
  was not yet settled
- **THEN** session restoration runs before fresh population initialization and settles the committed
  outcome, and the population owner does not delete, respawn or replace the recorded participant first

### Requirement: Startup combat restoration advances time only after every deterministic clock source is registered

The deterministic startup sequence SHALL run every deterministic sync that precedes session restoration — `sync_service_interiors()`, `sync_quest_runtime()`, `sync_guild_economy()`, `sync_guard_npc()`, and `sync_npc_schedules()` — before `restore_persisted_sessions()` may advance the world clock.

#### Scenario: All deterministic syncs precede session restoration, which precedes wilderness sync

- **WHEN** the `at_server_start()` call sequence is observed
- **THEN** `sync_service_interiors()`, `sync_quest_runtime()`, `sync_guild_economy()`, `sync_guard_npc()`, and `sync_npc_schedules()` all run strictly before `restore_persisted_sessions()`, which runs strictly before `sync_wilderness()`

#### Scenario: A due quest deadline inside a recovery window fails

- **WHEN** a cold start begins with an active quest whose `deadline_tick` falls inside the settlement window of a recovered invalid session
- **THEN** the quest record transitions to `FAILED` with reason `deadline_expired` during restoration, because `quest_deadlines` was already registered

#### Scenario: Restoration keeps its wilderness ordering and admits no bypass

- **WHEN** the startup sequence is composed
- **THEN** it still runs `restore_persisted_sessions()` before `sync_wilderness()` so a defeated
  population monster referenced by a committed session is never deleted or respawned first, and no
  recovery window can bypass an unregistered deterministic callback

#### Scenario: The recovery advance runs the ordinary registered stage set

- **WHEN** a recovered session's recovery advance runs `WorldClock.advance`
- **THEN** it runs the same registered stage set as any ordinary advance (`quest_deadlines`,
  `caravan_arrivals`, `shop_hours`, `npc_schedules`, plus `instance_reclamation` registered by
  `sync_grid`), which is why every deterministic sync precedes restoration

#### Scenario: Population sources are registered before catch-up
- **WHEN** session restoration advances world time
- **THEN** site and regional population sources and rollback contracts are already registered; fresh initialization never precedes protected session restoration

