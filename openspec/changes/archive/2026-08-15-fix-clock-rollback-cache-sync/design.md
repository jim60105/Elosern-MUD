## Context

`WorldClock.advance` (world/rules/clock.py:316-337) runs every stage inside one `transaction.atomic()` and, on exception, restores only `_ADVANCE_ENTITY_SURFACES` (world/rules/clock.py:228-238) on the caller-supplied entities plus the clock tick. Boundary-stage sources write durable state on objects outside that set:

- `quest_deadlines` discovers players via `PlayerCharacter.objects.all_family()` and replaces `quest_log` plus room `pin_reasons` (world/quests/deadlines.py:28-56, world/quests/transitions.py:119-140). Its own snapshot/restore fires only when its *nested* transaction raises; an outer failure after it returns leaves the cache stale.
- `caravan_arrivals` writes `merchant::merchant_stock` and `merchant::last_restock_day` host attributes (component DBFields persist as host attributes keyed `"{slot}::{field}"`, evennia/contrib/base_systems/components/dbfield.py) for every NPC host with a `Merchant` component (world/rules/caravan_arrivals.py:31-36, 72-85).
- `npc_schedules` writes `db.schedule_state` and relocates NPCs through stock `DefaultExit.at_traverse` (world/rules/npc_schedules.py:675-757), discovering NPCs by the `schedule` tag (world/rules/npc_schedules.py:815-819).
- `instance_reclamation` rewrites `expire_tick`/`named`/`interacted`/`pin_reasons`/`owned_entities` on `InstanceRoom`s, prunes `map_knowledge` on every player carrying the attribute (world/rules/map_knowledge.py:359-408), and deletes or relocates occupants (world/maps/instance.py:160-234).
- `shop_hours` is read-only (events only).

Evennia's Attribute writes update the cached model before saving (evennia/typeclasses/attributes.py), so a Django rollback restores rows but not in-process caches; manual snapshot/restore is the established pattern (world/rules/surfaces.py:16-55, world/rules/action.py:913-989) and is reused here. `register_event_source` (world/rules/clock.py:197-199) currently carries only the settlement callable; the registry is a plain module dict (`_EVENT_SOURCES`, world/rules/clock.py:58).

## Goals / Non-Goals

**Goals:**
- A failed `advance()` leaves every durable surface written by any registered boundary-stage source — quest logs and room pins, merchant stock, NPC schedule state and location, instance-room state, pruned map knowledge — equal to its pre-advance value in both the in-process cache and the rolled-back database.
- Registration is the single extension point: each writing source declares its surfaces next to its settlement function; no central hard-coded surface list grows.
- Deterministic and bounded: contracts are pure reads, run in fixed stage order before any write; stage order, the one-advance-one-day bound, and the `AdvanceSource.COMBAT` gate are untouched.
- Reusable by the parallel outer-settlement changes (`fix-movement-settlement-atomicity`, planned `fix-cast-clock-settlement`) so callback-owned surfaces are covered whichever transaction boundary fails.

**Non-Goals:**
- Changing settlement semantics, stage order, or the one-day budget.
- Making sources shareable across transactions or replayable (no event replay; a failed advance re-runs on the caller's next attempt).
- Wrapping `advance()` callers (commands, movement) in outer transactions — those are owned by the parallel changes.
- Audit-time discovery of "unregistered writes": the contract is a declaration, and a completeness test guards the four known writing sources; the read-only `shop_hours` seam is the documented exception.

## Decisions

**D1 — Advance-surface contracts on `register_event_source`.** Extend `register_event_source(kind, source, surfaces=None)` where `surfaces` is `Callable[[int, int], dict[int, SurfaceSnapshot]]`. `SurfaceSnapshot` is a small dataclass:

```python
@dataclass
class SurfaceSnapshot:
    attributes: dict[tuple[str, str | None], tuple[bool, Any]]  # (key, category) -> (existed, value)
    location: tuple[bool, int] | None = None  # (existed, pre-advance db_location pk) when the source may move the object
```

The location surface stores the **primary key**, never the live object: reading `db_location` returns an idmapper instance, and an object deleted inside the rolled-back transaction has `pk = None` on the stale instance — restoring `db_location` from that instance would set `db_location_id = None` and orphan the moved occupant. Storing the pk keeps the snapshot a pure read, JSON-safe, and restorable after rollback (rubber-duck review).

The two-argument form stays valid (test-seam sources and read-only sources), and `None` means "read-only seam". *Alternative considered:* a static per-kind surface table — rejected because which objects are touched is data-dependent (only due quests, only tagged NPCs), so the contract must re-discover objects per window, exactly like settlement.

**D2 — One merged pre-transaction registry.** A module function `build_advance_snapshot_registry(clock, seconds, source, entities) -> dict[int, SurfaceSnapshot]` merges, by object identity: (a) the existing caller-entity surfaces (`_ADVANCE_ENTITY_SURFACES`, unchanged), then (b) each registered stage kind's contract in `_STAGE_ORDER[5:]` order. Merging by identity means a caller-supplied player who also owns a due quest is snapshotted once with the union of surfaces. `advance()` calls this before opening its transaction and replaces `_snapshot_advance_entities` with the merged registry. A contract that raises fails the advance before any write (fail-closed, no partial state). *Alternative considered:* lazy snapshot-on-first-write inside settlement — rejected because the write-through Attribute cache already mutated by then, so the snapshot would capture the uncommitted value; only a pre-transaction read is sound.

**D3 — Restore semantics.** On any exception, after the rollback has completed (the `except` block runs after the `with transaction.atomic()` block exits): (a) restore the clock tick (existing `_restore_clock_tick`); (b) for each registry entry, in order: skip objects deleted during settlement — but do not assume the idmapper eviction happened: Evennia's `delete()` evicts only when `at_idmapper_flush()` returns True, which `TypedObject` overrides to False when the object holds any NAttribute, so restore must explicitly flush a cached-but-deleted entry (`is_deleted`) from the cache to force the next fetch to re-read the rolled-back rows; then restore each attribute surface via `restore_attribute_best_effort` (world/rules/surfaces.py:41-55); where `location` was recorded, re-fetch the target by its stored pk (`ObjectDB.objects.get(id=pk)` — after rollback this returns a fresh instance carrying the restored rows; a vanished target is skipped with a bounded diagnostic), assign that instance through the location setter so the rooms' contents caches are reconciled, and reset the re-fetched rooms' `contents_cache`; (c) run the existing `_refresh_advance_entity_caches` for caller-scope entities only. Attribute writes during restore create new rows matching the snapshot values — identical to the pre-advance rows, so cache and database converge (rubber-duck review: the deleted-room case, `instance.py:213` deleting a room whose occupants were relocated at `instance.py:141-157`, is exactly why location must be stored as a pk).

**D4 — Per-source contracts (declaration table).** Each writing source ships a `snapshot_*` function beside its settlement, reusing its exact discovery queries and the shared `attribute_snapshot`:

| kind | discovery (same as settlement) | surfaces |
|---|---|---|
| `quest_deadlines` | players with non-empty `quest_log` (all_family), plus every room referenced by any in-progress record's `stage_room_id` | `quest_log` (players); `pin_reasons` (rooms) — reuse `snapshot_quest_log`/`snapshot_pin_reasons` (world/quests/transitions.py:83-98) to avoid drift |
| `caravan_arrivals` | NPC hosts carrying the `Merchant` component | host attributes `merchant::merchant_stock`, `merchant::last_restock_day` |
| `npc_schedules` | NPCs tagged `schedule` | `schedule_state`; `location` on every tagged NPC (a move entry may relocate any of them) |
| `instance_reclamation` | every `InstanceRoom`; every player carrying `map_knowledge`; every non-owned `LivingEntity` occupant of each room | room `expire_tick`/`named`/`interacted`/`pin_reasons`/`owned_entities`; player `map_knowledge`; `location` of relocate-able occupants (restore also resets `DEFAULT_HOME`'s contents cache) |
| `shop_hours` | — | none (no contract; read-only seam) |

Room-pin snapshot for `quest_deadlines` covers the rooms `release_stage_binding` can unpin: for each in-progress record, the room with `id == record.stage_room_id` if it exists.

**D5 — Completeness guard.** A regression test asserts the four writing kinds are registered with contracts and that `shop_hours` is registered with `surfaces=None` (distinct assertions for each), plus one behavioral fault-injection test per source. This is a guard against a future source silently regressing to the un-snapshotted pattern, not a runtime check in the hot path.

**D6 — Nested-transaction composition with the parallel changes.** `advance()`'s own block degrades to a savepoint inside an outer `transaction.atomic()`; on inner failure `advance()` restores its own registry; on outer failure the outer owner must restore. The outer owners (`fix-movement-settlement-atomicity`, planned `fix-cast-clock-settlement`) SHALL build `build_advance_snapshot_registry` **before the outer transaction opens** and SHALL pair it with the clock-tick snapshot/restore (`_snapshot_clock_tick`/`_restore_clock_tick`), because a successful inner `advance()` followed by an outer-commit failure leaves both the callback-owned surfaces and the in-memory tick advanced. The movement change's current design consumes only `_ADVANCE_ENTITY_SURFACES` and treats its own D2 snapshots as the sole outer recovery; this change records the builder as the seam the movement and cast changes must be amended to consume, so callback-owned surfaces are covered whichever boundary fails. This change ships the builder with a focused test; the parallel changes wire it.

**D7 — Determinism and bounds.** Contracts execute in `_STAGE_ORDER[5:]` order before the transaction, read only, and cost the same discovery scans settlement already performs (bounded by the single-player world's player/NPC/room counts). `_STAGE_ORDER`, `MAX_ADVANCE_SECONDS`, and the `AdvanceSource.COMBAT` gate are not modified; a regression assertion keeps the fixed sequence intact. Kinds registered without a contract are skipped by the builder entirely, so plain `unittest.TestCase` advances never run contract DB queries; because `_EVENT_SOURCES` is module-global and existing tests already leak registrations into it, tests that register a contract-bearing source must clean up after themselves (or use the two-argument seam form), and the fault-injection tests reset the registry in `tearDown` (rubber-duck review).

## Risks / Trade-offs

- [Restoring attributes on an object deleted inside the failed transaction] → Deleted objects are skipped and, when the idmapper still holds the deleted instance (NAttribute case, `at_idmapper_flush()` False), explicitly flushed, so the next access re-fetches the rolled-back rows; the reclaimed-room test asserts the re-fetch returns a live object.
- [Location restore targeting a room deleted inside the failed transaction] → Location is snapshotted as a pk and re-fetched after rollback; a vanished target is skipped with a bounded diagnostic; the reclaim test asserts a relocated occupant points back into the re-fetched reclaimed room.
- [Component DBField backing keys are Evennia-contrib internals (`slot::field`)] → The caravan contract reads/writes through the host attribute API with the slot-prefixed keys, keeping the declaration next to `Merchant`; a behavioral test asserts cached and raw values converge, catching any key drift.
- [Location restore (db_location, contents caches) touches Evennia move internals] → Restore re-fetches the target by pk and assigns through the location setter so Evennia's contents caches are reconciled; exact cache-reset mechanics are verified in the NPC-move and instance-reclaim tests.
- [Contract snapshot cost grows with players/NPCs/rooms] → Same queries settlement already runs (a second pass per advance, acceptable at single-player scale); deepcopy cost is bounded by the world's object counts.
- [Double coverage when the parallel outer-settlement changes wrap advance] → Merged-by-identity registry dedupes; duplicate restore of the same value is idempotent.
- [A future source forgets its contract] → Completeness guard test fails loudly; the two-argument form keeps old test seams valid, so only writing sources must migrate.
- [The parallel movement change currently consumes only caller-entity surfaces] → D6 records the builder (plus tick snapshot/restore) as the seam its design must be amended to use; this change owns the builder, the movement change owns its outer boundary.

## Migration Plan

No released users and no data migration: the contracts are process-local declarations; existing saved games need no conversion. Registration sites and test seams are updated in the same change.

## Open Questions

- None blocking. The exact `contents_cache` reset mechanism (Evennia version specifics) is resolved during implementation by the NPC-move and instance-reclaim tests.
