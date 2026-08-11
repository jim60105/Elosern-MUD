## Context

`parse_duration` (`world/rules/time_skip.py:47-52`) caps nothing; `WorldClock.advance` (`world/rules/clock.py:217-226`) runs `_settle_gauge_regen` (durable attribute writes), `_settle_buffs_and_decay` (bounded by `max_settlement_quanta`), `_settle_boundary_stages` (unbounded per-day loop writing `reset_daily_counters`), then `persist(self.tick)` as a separate final write. Nothing wraps these in a transaction. The project already has an attribute snapshot/restore pattern in `world/rules/action.py:794-946` that this design reuses.

## Goals / Non-Goals

**Goals:**
- No partial advance survives a restart, for any clock source.
- One command can never drive an unbounded loop or an unbounded blocking settlement.

**Non-Goals:**
- Changing gauge-regen math (closed-form stays).
- Cross-entity atomicity beyond the caller-supplied entities (caller scoping stays per `world-clock`).

## Decisions

**D1 — Single cap constant.** `MAX_ADVANCE_SECONDS = rulebook/clock.yaml["max_sleep_seconds"]` (43200). `parse_duration` clamps to it; `WorldClock.advance` also enforces it defensively (named `ClockAdvanceBoundError`). This bounds the per-day loop to at most one day crossing per call.

**D2 — Transactional advance with snapshot/restore.** `advance()` snapshots the `SNAPSHOTTED_SURFACES`-style attributes of its caller-supplied entities, runs all stages plus the tick increment inside one `transaction.atomic()`, and restores snapshots on exception — reusing the same duck-typed snapshot/restore dispatch as `world/rules/action.py` (or the shared `world/rules/surfaces.py` helper) so idmapper caches stay consistent on rollback.

**D3 — Reject before write.** The bound check runs before any stage, so oversized calls never write anything.

## Risks / Trade-offs

- **Clock-source callers**: combat settlement passes `rounds_elapsed * 6s` — far below the cap; skip/movement scopes are unchanged. Cap check is a hard invariant, not a silent truncation, so accidental callers fail loudly.
- **Snapshot cost**: only caller-supplied entities are snapshotted (bounded by party size); the per-day loop events are computed but not persisted until commit.
- **Existing long rest saves**: project has no users; no migration needed.
