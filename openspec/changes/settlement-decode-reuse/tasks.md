# Tasks

Run only the focused commands named below. `/tmp/mud-test.env` holds the single line `MUD_TEST_SETTINGS=1`; "the test prefix" means `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`.
Do not add `covers_requirement` for ADDED requirements in this change; that happens at archive.
Do not edit `world/maps/monster_activity.py`, `world/maps/population_forecast.py`, `world/rules/` or any stored format. Do not add a wall-clock assertion.

## 1. Preconditions

- [ ] 1.1 Confirm `population-maintenance-log-tally` is merged: `uv run --locked python -c "import world.observability.tally"` exits 0. If not, stop and report.

## 2. Projection helper and differential test first

- [ ] 2.1 Create `world/maps/tests/_settlement_projection.py` per design D5.
- [ ] 2.2 Create `world/maps/tests/test_settlement_decode_reuse.py` with the differential test of design D6 only, and register the module in `.github/evennia-shards.json` beside `world.maps.tests.test_monster_activity`. Verify: the test prefix with `world.maps.tests.test_settlement_decode_reuse` passes against the unchanged production code (reuse on and off are equal today), and the test prefix with `tests.test_evennia_test_optimization_contract` passes.

## 3. Decode reuse

- [ ] 3.1 Apply design D1 and D2 to `world/maps/regional_population.py`, extracting `_timeline_from_raw` and `_zone_map_from_raw`. Add the decode-reuse tests of design D6. Verify: the test prefix with `world.maps.tests.test_settlement_decode_reuse` passes.
- [ ] 3.2 Verify nothing else moved: the test prefix passes for each of `world.maps.tests.test_regional_population`, `world.maps.tests.test_regional_population_recovery`, `world.maps.tests.test_population_zone_pass` (one command per module).

## 4. Pass-scoped facts

- [ ] 4.1 Apply design D3 and D4 to `world/maps/regional_population.py`, `world/maps/monster_sites.py` and `world/maps/population_lifecycle.py`, extracting `_protected_cells_at`. Add the pass-fact tests of design D6. Verify: the test prefix with `world.maps.tests.test_settlement_decode_reuse` passes.
- [ ] 4.2 Verify the owners' suites: the test prefix passes for each of `world.maps.tests.test_monster_activity`, `world.maps.tests.test_monster_journeys`, `world.maps.tests.test_monster_sites`, `world.maps.tests.test_wilderness_population`, `world.rules.tests.test_world_escape` (one command per label).

## 5. Documentation and gates

- [ ] 5.1 Apply design D7. Verify: `grep -c "Settlement read reuse" docs/development/regional-monster-population.md` prints 1.
- [ ] 5.2 Run `uv run --locked python -m tools.observability_lint check`, `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.contract_gate --change settlement-decode-reuse` and `openspec validate settlement-decode-reuse --strict`. Verify: all exit 0.
- [ ] 5.3 Information only, never a gate: if a profiling database copy is available, record in the hand-off the wall time and SQL statement count of one 3,580 second `clock.advance(seconds, AdvanceSource.COMMAND, [])` before and after this change. Skip this task without failing when no copy is available.

## Workflow follow-up

- During archive, after the delta sync, annotate the tests of the three ADDED requirements with the identifiers printed by `uv run --locked python -m tools.spec_traceability list`.
