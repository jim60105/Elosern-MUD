## Context

`submit_player_action` (`world/rules/combat_session.py:679-763`) commits round effects inside per-action `transaction.atomic()` blocks (`world/rules/action.py:972-979`), persists session metadata separately (`_persist`, `combat_session.py:506-507`), and `settle_session` (`:844-879`) chains further independent commits (exam outcome `guild_exams.py:379-392`, `clear_session`, `settle_combat_result` → tick persist, final clear). Termination windows leave half-round state, double-count hostile time (restore re-settles a terminal session), or lose exam time (exam clears before clock). Separately, `at_server_start` runs `sync_wilderness` before `sync_guild_economy` (`at_server_startstop.py:174-177`), and `ensure_population` deletes HP-0 population monsters (`wilderness_population.py:139-178`) before `restore_active_session` reads them, converting a committed win into defeat.

## Goals / Non-Goals

**Goals:**
- One round + its settlement as one durable unit.
- Terminal settlement idempotent across restart, regardless of crash point.
- Startup ordering protects session participants from reconciliation.

**Non-Goals:**
- Changing round semantics (mid-round rejections still keep prior turns per spec).
- Persisting live Battlefield objects (records stay JSON-safe dbref lists).
- Replay/migration of pre-existing split state (no users).

## Decisions

**D1 — Outer atomic + snapshot/restore around the whole round-and-settlement chain.** `submit_player_action` snapshots every touched entity (actor, companions, foes, battlefield, quest log) via the existing duck-typed snapshot dispatch, then runs run_round/overwhelm, friendly-fire scan, `_persist`, and `settle_session` inside one outer `transaction.atomic()`. Django savepoints make the nested per-action atomics harmless; the outer block gives whole-chain rollback.

**D2 — Durable settlement marker on the session record.** Add `settled_tick: int | None` to `CombatSessionRecord`. `settle_session` writes it inside the same transaction that advances the clock and clears the session; `restore_active_session` skips settlement for sessions already marked. Exam mode records the marker with the exam outcome instead of relying on clear-order.

**D3 — Startup ordering is owned by the companion change.** The restore-before-reconciliation startup ordering and the population participant guard live in `fix-startup-session-restore-order`; this change only guarantees that restored sessions are idempotent (D2) regardless of ordering.

## Risks / Trade-offs

- **Larger transaction scope**: holds the DB transaction over a full round; rounds are small (≤ a few participants, 12-round cap for overwhelm), acceptable for single-player.
- **Snapshot surface growth**: the snapshot set now includes all participants and the battlefield; reuse the existing handler registration so new surfaces raise instead of silently missing.
- **Marker writes on every persisted round**: `settled_tick` is only set at terminal settlement; `rounds_elapsed` still increments per round.
- **Landing order**: other combat changes (`fix-combat-session-roster-and-overwhelm`, `fix-friendly-fire-reachability`) apply their edits to `submit_player_action`/`settle_session` after this change lands, so the outer transaction seam is the shared owner.
