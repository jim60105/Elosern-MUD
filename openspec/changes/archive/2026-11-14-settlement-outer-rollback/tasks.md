# Tasks

Run only the focused commands named below. `/tmp/mud-test.env` holds the single line `MUD_TEST_SETTINGS=1`; "the test prefix" means `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`.
Do not add `covers_requirement` for ADDED requirements in this change; that happens at archive.
Do not edit `world/rules/field_contact.py`, any `snapshot_*_surfaces` function, `_restore_advance_registry`, or `regional_population.initialize_zones`. Do not add a wall-clock assertion.

## 1. Preconditions

- [x] 1.1 Confirm `settlement-decode-reuse` is merged: `test -f world/maps/tests/_settlement_projection.py` exits 0. If not, stop and report.

## 2. Flag and scope

- [x] 2.1 Apply design D1 to `world/rules/surfaces.py` and D2 to `world/rules/clock.py`. Create `world/maps/tests/test_settlement_outer_rollback.py` with the four pure flag tests of design D5 and register the module in `.github/evennia-shards.json` beside `world.maps.tests.test_monster_activity`. Verify: the test prefix with `world.maps.tests.test_settlement_outer_rollback` passes.
- [x] 2.2 Apply design D3 to `world/maps/population_lifecycle.py`. Add the differential test "Results are unchanged" of design D5. Verify: the same test label passes (both modes are still equal, because no site consults the flag yet).

## 3. The five sites

- [x] 3.1 Apply design D4 to `monster_activity._commit_stay` and `_commit_departure`. Add the test "Fault after a partial departure". Verify: the same test label passes, and the test prefix passes for `world.maps.tests.test_monster_activity` and for `world.maps.tests.test_monster_journeys`.
- [x] 3.2 Apply design D4 to `fatigue.settle_fatigue_intervals`. Add the test "Fault during a fatigue write". Verify: the same test label passes, and the test prefix passes for `world.rules.tests.test_fatigue`.
- [x] 3.3 Apply design D4 to `regional_population.commit_population_wave` / `_commit_planned_wave` and to `monster_sites.settle_site_recovery`. Add the test "Savepoints do not grow with the population". Verify: the same test label passes, and the test prefix passes for `world.maps.tests.test_regional_population_recovery` and for `world.maps.tests.test_monster_sites`.
- [x] 3.4 Add the test "Failed contact inside a pass" of design D5. Verify: the same test label passes, and the test prefix passes for `world.rules.tests.test_world_escape` and for `world.rules.tests.test_clock`.

## 4. Documentation and gates

- [x] 4.1 Apply design D6. Verify: `grep -c "Rollback ownership inside an advance" docs/development/monster-field-behaviour.md` prints 1.
- [x] 4.2 Run `uv run --locked python -m tools.observability_lint check`, `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.contract_gate --change settlement-outer-rollback` and `openspec validate settlement-outer-rollback --strict`. Verify: all exit 0.
- [x] 4.3 Information only, never a gate: if a profiling database copy is available, record in the hand-off the wall time, savepoint count and SQL statement count of one 3,580 second advance before and after this change. Skip without failing when no copy is available.
  Skipped: no profiling database copy is available (no Docker daemon, and `server/db/evennia.db3` is a zero-byte placeholder), so no advance could be timed. The savepoint count is instead bounded deterministically by the new module's `SavepointBoundTests`.

## Workflow follow-up

- During archive, after the delta sync, annotate the tests of the two ADDED requirements with the identifiers printed by `uv run --locked python -m tools.spec_traceability list`.