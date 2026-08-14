## 1. Clock registry protocol

- [ ] 1.1 In `world/rules/clock.py`, add a `SurfaceSnapshot` dataclass (`attributes: dict[tuple[str, str | None], tuple[bool, Any]]`, `location: tuple[bool, int] | None = None` — the pre-advance `db_location` stored as a plain pk, never a live object) and extend `register_event_source(kind, source, surfaces=None)` to store the optional contract beside the settlement callable; keep the two-argument form working for read-only and test seams
- [ ] 1.2 Add `build_advance_snapshot_registry(clock, seconds, source, entities) -> dict[int, SurfaceSnapshot]` that snapshots the existing `_ADVANCE_ENTITY_SURFACES` on caller entities and then runs every registered stage contract in `_STAGE_ORDER[5:]` order, merging by object identity; skip kinds registered without a contract; a raising contract fails the advance before any write
- [ ] 1.3 Rewrite `advance()` to build the merged registry before `transaction.atomic()` and, on exception, restore the tick, every registry attribute via `restore_attribute_best_effort`, and optional `location` (re-fetch the target room by its snapshot pk through `ObjectDB.objects.get`, assign via the location setter, reset the re-fetched rooms' `contents_cache`; a vanished target is skipped with a bounded diagnostic); skip registry objects deleted during settlement and explicitly flush any still-cached deleted instance (`is_deleted`, e.g. when NAttributes make `at_idmapper_flush()` return False) so the next fetch re-reads the rolled-back rows; keep the caller-entity cache refresh
- [ ] 1.4 Keep `_STAGE_ORDER`, `MAX_ADVANCE_SECONDS`, and the `AdvanceSource.COMBAT` gate untouched; add a regression assertion that the stage sequence is unchanged
- [ ] 1.5 Expose the outer-owner seam: a focused test proves `build_advance_snapshot_registry` + `_snapshot_clock_tick`/`_restore_clock_tick` can be built before an outer `transaction.atomic()` opens and restored after an outer-commit failure (the contract the parallel `fix-movement-settlement-atomicity` / planned `fix-cast-clock-settlement` changes must consume)

## 2. Per-source advance-surface contracts

- [ ] 2.1 `quest_deadlines` (world/quests/deadlines.py, registered in world/quests/bootstrap.py): contract snapshots `quest_log` for every player with a non-empty log (reusing `snapshot_quest_log`) and `pin_reasons` for every room referenced by any in-progress record's `stage_room_id` (reusing `snapshot_pin_reasons`)
- [ ] 2.2 `caravan_arrivals` (world/rules/caravan_arrivals.py): contract snapshots host attributes `merchant::merchant_stock` and `merchant::last_restock_day` for every NPC host carrying the `Merchant` component, using the same `_merchants()` discovery
- [ ] 2.3 `npc_schedules` (world/rules/npc_schedules.py): contract snapshots `schedule_state` and `location` for every schedule-tagged NPC (same `search_object_by_tag(SCHEDULE_TAG)` discovery)
- [ ] 2.4 `instance_reclamation` (world/maps/instance.py): contract snapshots room `expire_tick`/`named`/`interacted`/`pin_reasons`/`owned_entities` for every `InstanceRoom`, player `map_knowledge` for every player carrying the attribute (same filtered query as `prune_reclaimed_room`), and `location` (as pk) of every non-owned `LivingEntity` occupant (the `_clear_non_player_entities` relocation set)
- [ ] 2.5 `shop_hours`: register with no contract (`surfaces=None`) and leave its read-only behavior unchanged

## 3. Fault-injection tests (one per source; cache vs. raw storage)

- [ ] 3.1 `world/rules/tests/test_clock.py`: completeness guard (the four writing kinds registered with contracts and `shop_hours` registered with `surfaces=None`, as distinct assertions), registry merge/dedupe unit tests, contract-is-a-pure-read test, and the stage-order/bound regression assertion; fault-injection tests reset the leaked module-global `_EVENT_SOURCES` in `tearDown`
- [ ] 3.2 `world/quests/tests/test_deadlines.py`: due in-progress quest + later failing stage (and separately a failing final persist) leaves `player.db.quest_log`, the raw `quest_log` row, room `db.pin_reasons`, and the tick unchanged; successful advance with a due deadline still commits (no-regression)
- [ ] 3.3 guild-economy/caravan test: crossed restock day + failing persist leaves cached and raw `merchant::merchant_stock`/`merchant::last_restock_day` equal to pre-advance values
- [ ] 3.4 `world/rules/tests/test_npc_schedule_runtime.py`: settled `state` and `move` occurrences + failing persist restore cached and raw `schedule_state`, the NPC's `db_location`, and the source/destination rooms' contents; update the existing registration-source string assertion to accept the contract form of `register_event_source` (task 2.3 changes the call shape)
- [ ] 3.5 `world/maps/tests/test_instance_reclamation.py`: promote/reclaim + `map_knowledge` prune + failing persist restores room surfaces and the pruned player knowledge in cache and storage; a relocated occupant's location points back into the re-fetched reclaimed room (never the deleted instance or `None`); a deleted-then-rolled-back room re-fetches as a live object even when it carried an NAttribute
- [ ] 3.6 Annotate the new main-spec requirement tests with `covers_requirement` using canonical IDs from `uv run --locked python -m tools.spec_traceability list`

## 4. Verification

- [ ] 4.1 Run `uv run --locked python -m compileall -q world typeclasses commands server`
- [ ] 4.2 Run the focused suites: `world.rules.tests.test_clock`, `world.quests.tests.test_deadlines`, `world.rules.tests.test_npc_schedule_runtime`, `world.maps.tests.test_instance_reclamation`, and the guild-economy tests
- [ ] 4.3 Run `openspec validate --change fix-clock-rollback-cache-sync --strict` and `uv run --locked python -m tools.spec_traceability check`; keep `git diff --check` clean
