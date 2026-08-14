## ADDED Requirements

### Requirement: The npc_schedules clock source is registered before startup combat recovery advances time

The server `at_server_start()` composition root SHALL call `sync_npc_schedules()` — and through it `register_npc_schedules()` — before `restore_persisted_sessions()` may advance the world clock, so every schedule occurrence whose due tick falls inside a startup recovery settlement window (`start_tick < due_tick <= end_tick`, `due_tick >= effective_from_tick`) settles exactly as it would in an ordinary advance. The settlement window produced by a recovered session's accumulated rounds SHALL NOT lose an occurrence to an unregistered `npc_schedules` stage, and no later sync or backfill SHALL be required to recover it.

#### Scenario: A recovery advance settles an occurrence due inside its window

- **WHEN** a cold start begins at tick 0 with an NPC whose schedule is effective from tick 0 and has a `state` entry due at tick 3, and a well-formed one-round persisted session that is terminated as invalid (recorded enemy deleted) settles through restoration, advancing the clock from 0 to 6
- **THEN** the tick-3 occurrence settles: the NPC's `schedule_state` holds the entry's state and a `npc_state_changed` event with the entry's due tick is produced, exactly as if `advance(6, ...)` had run with `npc_schedules` registered

#### Scenario: The stage source is registered from startup, not lazily

- **WHEN** `at_server_start()` has completed its deterministic sync sequence
- **THEN** the clock's registered `npc_schedules` source is `settle_npc_schedules` and it was registered before any startup-time world advance
