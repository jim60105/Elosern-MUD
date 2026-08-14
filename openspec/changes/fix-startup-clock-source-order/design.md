## Context

`at_server_start` (`server/conf/at_server_startstop.py:168-184`) currently runs:

```
get_world_clock(); sync_all(); sync_limbo(); sync_grid();
restore_persisted_sessions();            # :178
sync_wilderness();
sync_service_interiors(); sync_quest_runtime(); sync_guild_economy();
sync_guard_npc(); sync_npc_schedules();
```

Only `sync_grid` registers a clock source (`register_instance_reclamation()`, `world/maps/bootstrap.py:231`). `restore_active_session` (`world/rules/combat_session.py:1250-1290`) settles a terminally-outcome or invalid session through `settle_session` → `settle_combat_result` → `WorldClock.advance(rounds * 6, COMBAT, ...)` (`world/rules/clock.py:316-337`, `:376-378`). `_run_stages` → `_settle_boundary_stages` (`clock.py:202-214`) queries `_EVENT_SOURCES` per kind and treats an unregistered kind as producing zero events — no error, no backfill. During restoration, `quest_deadlines` (`world/quests/bootstrap.py:28-38`), `caravan_arrivals`/`shop_hours` (`world/rules/guild_economy.py:138-154`), and `npc_schedules` (`world/rules/npc_schedules.py:556-590`) are not yet registered, so `(start_tick, end_tick]` windows crossed by the recovery advance are lost for every source; `_due_occurrences` (`world/rules/npc_schedules.py:760-791`) never replays an occurrence before the current window. Worst case is 99 rounds (`_round_cap`, `combat_session.py:1021-1022`) × 6 s = 594 s.

The startup composition root must keep `restore_persisted_sessions()` before `sync_wilderness()`: a defeated wilderness population monster still referenced by a committed session must not be deleted or respawned first (`fix-startup-session-restore-order` D1, `world/maps/wilderness_population.py:149-183`).

## Goals / Non-Goals

**Goals:**
- Every world-time advance, including startup recovery settlement, runs the complete registered stage set.
- Keep `restore_persisted_sessions()` before `sync_wilderness()`.
- Deterministic, cold-start-safe with no dependency on process state from a previous run.

**Non-Goals:**
- Changing `_STAGE_ORDER` or the "unregistered source = zero events" seam contract (`settlement-stage-order`).
- Changing `restore_active_session` settlement semantics or malformed-record handling (owned by `fix-malformed-combat-recovery`).
- Backfilling already-lost windows retroactively — the fix prevents the loss, it cannot replay history.
- Persisting battlefield objects or altering wilderness reconciliation behavior for monsters no session references.

## Decisions

**D1 — Reorder the full syncs ahead of session restoration.** The new `at_server_start` sequence:

```
get_world_clock(); sync_all(); sync_limbo(); sync_grid();          # instance_reclamation
sync_service_interiors();                                          # needs grid exteriors
sync_quest_runtime();                                              # quest_deadlines + quest planner
sync_guild_economy();                                              # caravan_arrivals, shop_hours
sync_guard_npc();                                                  # needs grid South Gate
sync_npc_schedules();                                              # npc_schedules
restore_persisted_sessions();                                      # still before sync_wilderness (D1)
sync_wilderness();
```

Each moved sync is idempotent, never advances time, and has no dependency on session restoration or wilderness reconciliation (verified: quest runtime reads only the quest catalog/store; guild economy reads catalog, service interiors, and merchants; guard sync needs only the grid; schedule sync needs only the rulebook and existing NPCs). The five moved syncs keep their relative order, so every existing relative-order guard (`quest` before `guild_economy`, `guard` before `npc_schedules`, grid before both) stays valid.

**D2 — Full syncs, not a register-early/sync-later split.** The alternative — calling `register_npc_schedules()` (and friends) early while deferring the full sync passes — was rejected: each register function exists precisely because the matching sync is the composition-root step, and registration is only meaningful once the source's registries/catalogs exist (e.g. `sync_guild_economy` loads the catalog before `_register_clock_sources`; `sync_npc_schedules` registers only after `_sync_npc_schedules` has validated the rulebook and deactivated the layer — removing every `schedule` tag — on failure). Moving the complete idempotent syncs preserves "register only after its data is initialized" with one ordering, one code path, and no duplicated registration calls.

**D3 — Preserve the archived D1 constraint by construction.** `restore_persisted_sessions()` and `sync_wilderness()` remain adjacent and in that order, unchanged from `fix-startup-session-restore-order`; the change moves only the five syncs that previously ran after `sync_wilderness` to before restoration. Source-order guards (the repo's established pattern: `world/maps/tests/test_bootstrap.py`, `world/rules/tests/test_guild_economy_guards.py`) plus one behavioral ordering test pin this sequence.

## Risks / Trade-offs

- **Ordering sensitivity** → The composition root is guarded by source-index assertions (every clock-source sync before `restore_persisted_sessions()`, restoration before `sync_wilderness()`) and a behavioral invocation-order twin; `openspec validate` plus the affected package suites run at handoff.
- **Moved syncs depend on earlier stages** → Verified: service interiors require the grid (still before them); guild economy requires interiors (still before it); guard requires the grid; schedules require only data files. No moved step regresses.
- **`test_deadlines.py` source guard asserts the old order** → Inverted in the same change (implementation task 1.2), keeping the quest "after lore and map sync" requirement intact.
- **Recovery advance runs with the full stage set, so a source failure could raise during restoration** → Each stage's settlement is exception-isolated within `_settle_boundary_stages` (per-source execution) and restoration already wraps per-player settlement in try/except. Note the failure-mode shift for unwrapped syncs: `sync_quest_runtime` and `sync_guild_economy` raise loudly by design (e.g. `restore_generated_quests`), so under the new order a quest/economy sync failure aborts startup *before* session restoration instead of after. Every sync is idempotent and re-run on the next boot, so a failed boot leaves sessions untouched and self-heals on restart; this is an accepted, documented trade-off, not a new failure surface beyond the syncs' existing loud-failure contract.
- **No user data** → No migration; project has no released users.

## Migration Plan

None — startup-order-only change; `at_server_start` is idempotent across restarts and reloads, and re-running the moved syncs over existing state is a no-op by design.

## Open Questions

None.
