## Context

`at_server_start` runs `sync_wilderness()` before `sync_guild_economy()` (`server/conf/at_server_startstop.py:174-177`). `ensure_population` (`world/maps/wilderness_population.py:146-178`) deletes HP-0 population monsters (`_matches_expected` requires `_stored_hp > 0`, `:139-143`) before `_restore_persisted_sessions` (`world/rules/guild_economy.py:151-163`) reads the session, so `reconstruct_battlefield` raises `MISSING_PARTICIPANT` and `restore_active_session` settles the committed win as defeat (`combat_session.py:919-923`).

## Goals / Non-Goals

**Goals:**
- Session participants are never destroyed by reconciliation before settlement.
- Reconciliation behavior for session-free monsters is unchanged.

**Non-Goals:**
- Changing settlement atomicity or idempotency (owned by `fix-combat-settlement-recovery`).
- Persisting battlefield objects.

## Decisions

**D1 — Reorder startup: restore sessions before `sync_wilderness`.** Move the persisted-session restoration step (currently inside `sync_guild_economy`) ahead of wilderness sync; `sync_guild_economy` has no dependency on wilderness sync, so the reorder is safe.

**D2 — Participant guard in `ensure_population` (defense in depth).** Before deleting/replacing a marker monster, check whether any persisted `active_combat` record references its dbref; if so, skip it for this reconciliation pass. This protects sessions even if startup ordering regresses.

## Risks / Trade-offs

- **Ordering sensitivity**: the reorder is the primary fix; the guard covers regressions. Both are cheap and tested.
- **No user data**: no migration for existing split-state saves (project has no users).
