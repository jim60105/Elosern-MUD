# Tasks

## 1. Resident vocabulary and source kind

- [ ] 1.1 Add the frozen `Resident` dataclass and empty-but-validated `RESIDENT_REGISTRY` under `world/lore/` (per-village slices layout), with the `key`/`name`/`profile_key`/`race`/`subrace`/`sex`/literal `stats`/`home_room`/`schedule_template`/`dialogue_key` fields from design D1. Verify: module imports, key-uniqueness and elf-band validation reject a synthetically malformed row.
- [ ] 1.2 Add a `resident` source kind to `world/lore/npc_profiles/inventory.py::NpcSource` (keyed by resident key, owner = village slice) and wire `world.lore.tests.test_npc_profile_inventory` to derive resident sources from `RESIDENT_REGISTRY`. Verify: the inventory data-contract test passes with the extended kind.

## 2. Resident sync and route generalisation

- [ ] 2.1 Implement `world/rules/resident_sync.py::sync_residents()` per design D2: validate roster first, resolve every home room and schedule move target fail-closed, then find-or-create each resident as an `LLMNPC` in one transaction and assemble persona from its `NpcProfile` (never overwriting player edits), canonical ages, literal trait config, `sex`, and a binding-less `scripted_dialogue` component when a `dialogue_key` is present. Verify: a focused synthetic-group test proves construction, complete card, literal stats, correct sex, and absence of every managed service component.
- [ ] 2.2 Make the sync place a newly created resident in its home and assign its schedule via `set_npc_schedule` (existing `resident` template + per-resident target overrides binding `residence`→home dbref and `market_square`→public-space dbref); roll back restored caches and evict created objects on failure. Verify: focused tests prove home placement, schedule assignment, idempotent re-sync (no duplicate, edits preserved), and wholesale rollback on an unresolved room.
- [ ] 2.3 Generalise the second endpoint of `resolve_residence_route` (or add a parallel resolver) from a guild place to a village public-space room, returning the same `{home, public, frontage}` shape. Verify: the existing adventurer route test still passes and a new route test proves home↔public↔frontage resolution and disconnect rejection.

## 3. Roster, editorial and startup integration

- [ ] 3.1 Extend `npc_persona_roster_validation` and (if needed) `world/lore/npc_editorial_review.py`'s per-kind face declaration so residents are checked for profile references, single-dialogue ownership, canonical-identity uniqueness, and no orphan profile/table. Verify: `world/lore.tests.test_npc_editorial_review` and the roster-validation focused test pass.
- [ ] 3.2 Register the resident sync in `STARTUP_STEP_ORDER` after `npc_persona_roster_validation` and before `sync_all`. Verify: the startup-step-order contract test passes and reports the step at the correct index.

## 4. Integration verification

- [ ] 4.1 Run the focused dialogue/schedule/roster Evennia labels plus the new resident-sync/route tests; then `uv run --locked python -m tools.contract_gate`, `uv run --locked python -m tools.test_data_lint check`, and `uv run --locked python -m tools.spec_traceability check`. Verify: all green.

## Workflow follow-up

- Archive `elven-resident-npcs-mechanism` before starting `elven-resident-npcs-content` (the content change depends on this one's completed registry/sync/route generalisation).
- Verify the archived result.