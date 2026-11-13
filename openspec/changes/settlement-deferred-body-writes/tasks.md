# Tasks

Run only the focused commands named below. `/tmp/mud-test.env` holds the single line `MUD_TEST_SETTINGS=1`; "the test prefix" means `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`.
Do not add `covers_requirement` for ADDED requirements in this change; that happens at archive.
Do not change any read site, any stored format, `monster_activity.batched_state_writes`, or any Evennia class. Do not add a wall-clock assertion.

## 1. Preconditions

- [ ] 1.1 Confirm `settlement-outer-rollback` is merged: `uv run --locked python -c "from world.rules.surfaces import outer_rollback_owner, owned_atomic; from world.rules.clock import advance_registry_held"` exits 0. If not, stop and report.

## 2. Buffer

- [ ] 2.1 Apply design D1 to `world/rules/surfaces.py` (including `attribute_stores_deferred()`). Create `world/maps/tests/test_settlement_deferred_writes.py` with the pure buffer tests of design D6 and register the module in `.github/evennia-shards.json` beside `world.maps.tests.test_monster_activity`. Verify: the test prefix with `world.maps.tests.test_settlement_deferred_writes` passes.
- [ ] 2.2 Apply design D2 to `world/maps/population_lifecycle.py`. Add the differential test "Results are unchanged". Verify: the same test label passes (no site defers yet, so both modes are equal).

## 3. Write sites

- [ ] 3.1 Apply design D3 and D4 to `world/maps/regional_population.py`, `world/maps/monster_activity.py` and `world/maps/monster_sites.py`. Add the tests "Statements do not grow with boundary ticks" (timeline and coordinate rows), "Readers see pending values", "Contact sees stored state" and "Fault after deferred writes". Verify: the same test label passes, and the test prefix passes for each of `world.maps.tests.test_monster_activity`, `world.maps.tests.test_monster_journeys`, `world.maps.tests.test_regional_population_recovery`, `world.maps.tests.test_monster_sites`, `world.maps.tests.test_settlement_decode_reuse`, `world.maps.tests.test_settlement_outer_rollback` (one command per label).
- [ ] 3.2 Apply design D3 to `fatigue.write_fatigue_state`. Extend "Statements do not grow with boundary ticks" with the reserve rows. Verify: the same test label passes, and the test prefix passes for `world.rules.tests.test_fatigue`.
- [ ] 3.3 Apply design D5 to `clock._settle_gauge_regen`. Add the test "Three regenerating gauges". Verify: the same test label passes, and the test prefix passes for `world.rules.tests.test_clock` and for `world.rules.tests.test_world_escape`.

## 4. Documentation and gates

- [ ] 4.1 Apply design D7. Verify: `grep -c "Deferred stores inside an advance" docs/development/monster-field-behaviour.md` prints 1.
- [ ] 4.2 Run `uv run --locked python -m tools.observability_lint check`, `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.contract_gate --change settlement-deferred-body-writes` and `openspec validate settlement-deferred-body-writes --strict`. Verify: all exit 0.
- [ ] 4.3 Information only, never a gate: if a profiling database copy is available, record in the hand-off the wall time and the count of `UPDATE typeclasses_attribute` statements of one 3,580 second advance before and after this change. Skip without failing when no copy is available.

## Workflow follow-up

- During archive, after the delta sync, annotate the tests of the three ADDED requirements with the identifiers printed by `uv run --locked python -m tools.spec_traceability list`.
