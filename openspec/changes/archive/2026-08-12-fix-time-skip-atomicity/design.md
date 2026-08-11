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

**D1 — Two bounds, both derived from the same rulebook.** `MAX_SKIP_SECONDS = rulebook/clock.yaml["max_sleep_seconds"]` (43200) caps the `rest` command's parsed duration, matching `sleep` and the Web bound. `MAX_ADVANCE_SECONDS` is the defensive per-call advance budget in `world/rules/clock.py`, set to one full game day (`seconds_per_hour * hours_per_day` = 86400): `wait until`'s worst case is a full-day wait, and the hard raise must never make it fail (task 1.2 keeps it "bounded by a day"). One day also bounds the per-day loop at exactly one crossing per call and leaves every sanctioned caller legal (combat caps at `max_rounds * 6s`; move/cast are seconds-scale). `parse_duration` clamps to `MAX_SKIP_SECONDS`; `WorldClock.advance` raises a named `ClockAdvanceBoundError` above `MAX_ADVANCE_SECONDS` before any stage runs.

**D2 — Transactional advance with snapshot/restore.** `advance()` snapshots the `SNAPSHOTTED_SURFACES`-style attributes of its caller-supplied entities, runs all stages plus the tick increment inside one `transaction.atomic()`, and restores snapshots on exception — reusing the same duck-typed snapshot/restore dispatch as `world/rules/action.py` (or the shared `world/rules/surfaces.py` helper) so idmapper caches stay consistent on rollback. The in-memory tick and the persisted `world_clock` Script's `tick` attribute are snapshotted and restored the same way, so a failure at the final `persist()` (or at commit) leaves both the live clock and the stored tick at the pre-advance value.

**D2a — Nested-transaction ownership.** When another subsystem (the combat-settlement recovery change) wraps `advance()` in its own outer `transaction.atomic()`, the inner block degrades to a Django savepoint and only that inner failure triggers `advance()`'s restore. A later failure of the outer transaction rolls back the writes but is the outer owner's responsibility to snapshot/restore; `advance()`'s in-memory tick must be re-read after an outer rollback.

**D3 — Reject before write.** The bound check runs before any stage, so oversized calls never write anything.

## Risks / Trade-offs

- **Clock-source callers**: combat settlement passes `rounds_elapsed * 6s` — far below the cap; skip/movement scopes are unchanged. Cap check is a hard invariant, not a silent truncation, so accidental callers fail loudly.
- **Snapshot cost**: only caller-supplied entities are snapshotted (bounded by party size); the per-day loop events are computed but not persisted until commit.
- **Existing long rest saves**: project has no users; no migration needed.
