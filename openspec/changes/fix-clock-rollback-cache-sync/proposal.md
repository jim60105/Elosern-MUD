## Why

`WorldClock.advance` wraps every stage in one database transaction but snapshots only a fixed set of surfaces on the caller-supplied entities (`_ADVANCE_ENTITY_SURFACES`, world/rules/clock.py:228-238). Boundary-stage sources write durable state on objects `advance()` never sees: `quest_deadlines` rewrites `quest_log` and room pins on players it discovers itself (world/quests/deadlines.py:28-56), `caravan_arrivals` rewrites merchant stock, `npc_schedules` rewrites schedule state and relocates NPCs, and `instance_reclamation` rewrites instance-room state and prunes map knowledge. When a later stage or the final tick persist fails, Django rolls the rows back but the same in-process objects keep the rolled-back future state in their Evennia Attribute caches; later quest operations can consume and repersist state that never committed (audit finding, severity medium: likelihood low, impact high).

## What Changes

- Extend `register_event_source` so every boundary-stage source may declare an **advance-surface contract**: a pure read that re-discovers the exact objects its settlement can write and snapshots each durable surface (and optional location state) through the shared `attribute_snapshot` helper.
- Make `WorldClock.advance` snapshot **all** declared surfaces — caller-entity surfaces plus every registered stage contract, merged in stage order — before opening the transaction, and restore all of them (attributes, handler caches, NPC/entity locations, room contents caches) after any exception, reusing the existing best-effort restore pattern.
- Ship contracts for the four writing sources: `quest_deadlines` (`quest_log`, room `pin_reasons`), `caravan_arrivals` (merchant `merchant_stock`, `last_restock_day` host attributes), `npc_schedules` (`schedule_state` plus NPC location), `instance_reclamation` (instance-room `expire_tick`/`named`/`interacted`/`pin_reasons`/`owned_entities`, pruned player `map_knowledge`, relocated-entity locations). `shop_hours` stays a read-only seam with no contract.
- Keep the fixed stage order, the one-advance-one-day bound, the `AdvanceSource.COMBAT` gate, and the caller-scoping contract intact; the change is scoped to rollback coherence of `advance()`.
- Add fault-injection tests per source proving the in-process cache matches raw Attribute storage after a rolled-back advance.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `world-clock`: the "advance() persists the tick and entity state atomically" requirement is extended from caller-entity surfaces to every durable surface written by any registered boundary-stage source, with per-source rollback scenarios; a new requirement makes every writing source declare its advance-surface contract.

## Impact

- `world/rules/clock.py` (registration API, snapshot-registry builder, `advance()` restore path).
- `world/quests/deadlines.py` + registration in `world/quests/bootstrap.py` (quest contract).
- `world/rules/caravan_arrivals.py` (merchant contract).
- `world/rules/npc_schedules.py` (schedule contract).
- `world/maps/instance.py` (instance contract).
- `world/rules/shop_hours.py` (no contract; unchanged behavior, documented seam).
- Tests: `world/rules/tests/test_clock.py`, `world/quests/tests/test_deadlines.py`, `world/rules/tests/test_npc_schedule_runtime.py`, `world/maps/tests/test_instance_reclamation.py`, guild-economy merchant tests.
- Related parallel changes (non-overlapping): `fix-movement-settlement-atomicity` (movement post-traverse outer boundary) and the planned `fix-cast-clock-settlement` (out-of-combat cast outer boundary) both wrap `WorldClock.advance` in outer transactions; this change provides the reusable merged snapshot-registry builder those outer owners must reuse so callback-owned surfaces are covered whichever boundary fails. No dependency, migration, or data-schema impact; project has no released users.
