## Why

On a cold start, `at_server_start` registers only `instance_reclamation` (via `sync_grid`) before `restore_persisted_sessions()` advances the world clock while settling recoverable combat sessions. The clock advance inside that recovery therefore runs with `quest_deadlines`, `caravan_arrivals`, `shop_hours`, and `npc_schedules` unregistered, so any schedule occurrence or quest deadline due inside the recovery window is silently skipped and can never be backfilled (`_due_occurrences` covers only the current window). A well-formed one-round session can skip a window of up to 99 rounds × 6 s = 594 s (audit finding run-3 index 7).

## What Changes

- The deterministic startup sequence registers **every** world-event clock source before any startup operation can advance time: quest runtime, guild economy, guard NPC, and NPC-schedule syncs all move ahead of persisted-session restoration.
- `restore_persisted_sessions()` stays strictly **before** `sync_wilderness()` (preserves `fix-startup-session-restore-order` D1).
- No change to `_STAGE_ORDER` or the "unregistered source produces no events" clock contract: unregistered stages remain legal, but the startup composition root can no longer produce a time advance with sources missing.
- No change to `restore_active_session` settlement semantics; the recovery window merely runs the complete stage set.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `npc-schedule-runtime`: the `npc_schedules` clock source is registered before startup combat recovery can advance time, so occurrences due inside a recovery window settle like any ordinary advance.
- `player-combat-session`: startup session restoration advances time only after every deterministic clock source is registered, while still running before wilderness population reconciliation.

## Impact

- `server/conf/at_server_startstop.py` (`at_server_start` call order only).
- Ordering guard tests that assert the old order:
  - `world/quests/tests/test_deadlines.py::test_server_start_calls_quest_sync_after_map_sync` asserts `sync_wilderness() < sync_quest_runtime()` and must be inverted.
  - `world/rules/tests/test_guild_economy_guards.py` guards (restore before wilderness, quest after map, guard before schedules) remain valid; add guards asserting every deterministic sync precedes `restore_persisted_sessions()`.
- New regression tests: a cold-start probe proving a one-round invalid session advancing the clock 0 → 6 does not skip a tick-3 NPC occurrence, and a quest-deadline probe proving a deadline inside a recovery window fails; the wilderness participant-protection test (`world/maps/tests/test_wilderness_population.py::test_restart_settles_committed_victory_before_reconciliation`) must stay green.
- The two delta requirements are synced into `openspec/specs/` during implementation so their `covers_requirement` IDs enter the traceability index (repo rule: an annotation is added only once the main requirement ID exists).
- `docs/gm/operations.md` ("啟動順序") documents the old startup order and is updated in the same change.
- No data migration, no API change; project has no released users.
