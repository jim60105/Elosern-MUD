# Tasks

"The test prefix" means `uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb`. Run each test command standalone (no pipe, no redirect), with one dotted label.
Do not add `covers_requirement` for the ADDED requirements of this change; that happens at archive.
Tests use synthetic zones, areas and groups only (the fixtures of `world/maps/tests/test_scoped_population_settlement.py` and `world/maps/tests/test_monster_activity.py`). No test asserts elapsed real time; work is asserted by call counts and object identity.
Do not edit any owner operation, any single-entry codec, `MonsterActivityState`, `_copy_state`, `batched_state_writes`, `unbatched_state_writes`, `world/maps/population_units.py`, `world/maps/population_lifecycle.py` or `world/maps/population_drain.py`. Do not write a migration.

## 1. Storage

- [x] 1.0 Confirm `monster-activity-record-access` is merged. Verify: `grep -c "def read_stored_monster_activity\|def write_monster_activity" world/maps/monster_activity.py` prints 2. If not, stop and report.

- [x] 1.1 In `world/maps/monster_activity.py` add `MONSTER_ACTIVITY_PART_CATEGORY`, `_HEADER_FIELDS`, `_PART_FIELDS` and `part_key` (design D1), `_Part`, `_Assembled`, `_ASSEMBLED`, `_cross_check`, `_part_from_dict` and `_assemble`, and rewrite `read_stored_monster_activity` and `read_monster_activity` (design D3). Remove `_DECODED_STATE`. Export `MONSTER_ACTIVITY_PART_CATEGORY` and `part_key` in `__all__`. Verify: `grep -c "_DECODED_STATE" world/maps/monster_activity.py` prints 0.
- [x] 1.2 Add `_store_part` and `_store_state`, and make the stored branch of `_write_state` call `_store_state` (design D2, D4). Update the docstrings of `state_to_dict` and `state_from_dict` (design D5). Verify: `grep -c "wilderness.db.monster_activity = " world/maps/monster_activity.py` prints 0.
- [x] 1.3 Create `world/maps/tests/test_monster_activity_parts.py` on `ScopedSettlementFixture` (import it from `world.maps.tests.test_scoped_population_settlement`) with one test per scenario of the first three requirements of the delta spec: round trip after `self.wilderness.attributes.reset_cache()`; placement by home unit (read each part with `wilderness.attributes.get(part_key(unit), category=MONSTER_ACTIVITY_PART_CATEGORY)`); a group keeps its part after its home is rewritten; other parts not rewritten (`assertIs` on the second part's `return_obj=True` attribute `db_value` before and after); a batched pass stores its parts once (patch `world.maps.monster_activity._store_part` with `wraps=` and assert the units it was called with); unchanged state stores nothing (same patch, plus the header's `db_value` identity); malformed header; missing part; duplicate entry (store a second part holding the same group through `wilderness.attributes.add` and list it in the header). Each of the three refusal tests also patches `_store_part` and asserts it was not called and that the header's stored `db_value` is the same object after the failed read. Then run `uv run --locked python -m tools.shard_register fix` (do not edit `.github/evennia-shards.json` by hand). Verify: the test prefix with `world.maps.tests.test_monster_activity_parts` passes and `uv run --locked python -m tools.contract_gate manifests contracts` exits 0.

## 2. Rollback surfaces

- [x] 2.1 Add `activity_record_surfaces` and use it in `snapshot_activity_surfaces` and in `regional_population.snapshot_population_surfaces` (design D6). Export it. Verify: `grep -n "\"monster_activity\", None" world/maps/regional_population.py` prints nothing.
- [x] 2.2 In `world/maps/tests/test_monster_activity_parts.py` add the two scenarios of "A rolled-back activity write restores every part". For each: take `surfaces = monster_activity.snapshot_activity_surfaces(self.wilderness, member_ids=())`, open `transaction.atomic()`, perform the write (a group change through `write_monster_activity`; a `create_group` in a unit with no part), raise inside the block, catch outside it, call `monster_activity.restore_activity_surfaces(surfaces, wilderness=self.wilderness)`, then assert the record from memory and after `self.wilderness.attributes.reset_cache()` equals the prior `state_to_dict`, and for the created part that `attributes.has(part_key(unit), category=MONSTER_ACTIVITY_PART_CATEGORY)` is false and a second `create_group` in that unit succeeds. Verify: the test prefix with `world.maps.tests.test_monster_activity_parts` passes.
- [x] 2.3 Run `grep -n "member_time\[" world/maps/monster_activity.py world/maps/regional_population.py world/maps/monster_sites.py world/rules/*.py`. Verify: every hit assigns into a local copy made in the same function (`dict(...)` or a comprehension), never into the `member_time` of a group read from the state; record the hits in the hand-off. If a hit mutates a stored group in place, change it to copy first and say so in the hand-off.

## 3. Existing tests and documentation

- [x] 3.1 Apply design D8 to the two tests it names. Verify: the test prefix passes for each of `world.maps.tests.test_monster_activity`, `world.maps.tests.test_monster_journeys`, `world.maps.tests.test_population_units`, `world.maps.tests.test_population_drain`, `world.maps.tests.test_settlement_outer_rollback` (one command per label).
- [x] 3.2 Verify the remaining consumers: the test prefix passes for each of `world.maps.tests.test_regional_population`, `world.maps.tests.test_regional_population_recovery`, `world.maps.tests.test_monster_sites`, `world.maps.tests.test_scoped_population_settlement`, `world.maps.tests.test_population_catch_up`, `world.rules.tests.test_field_contact_boundaries` (one command per label; when a label discovers more than 100 tests, run its classes or submodules separately).
- [x] 3.3 Apply design D7 to both documents. Verify: `grep -c "Activity record storage" docs/development/regional-monster-population.md` prints 1.

## 4. Gates

- [x] 4.1 Run `uv run --locked python -m tools.observability_lint check`, `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.contract_gate` and `openspec validate monster-activity-record-parts --strict`. Verify: all exit 0.
- [x] 4.2 Observation, recorded in the hand-off as information only and never a gate: when a provisioned development database is available, time one `drain_population_backlog(600)` call from `evennia shell` before and after this change and note both numbers. Skip and say so when no such database exists.

## Workflow follow-up

- During archive, after the delta sync, annotate the tests of the four ADDED requirements with the identifiers printed by `uv run --locked python -m tools.spec_traceability list`.
- Recreate the development and live databases after the merge; the stored format is incompatible.
