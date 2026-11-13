# Tasks

Run only the focused commands named below. `/tmp/mud-test.env` holds the single line `MUD_TEST_SETTINGS=1`; "the test prefix" means `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`.
Do not add `covers_requirement` for ADDED requirements in this change; that happens at archive.
Do not edit `world/rules/clock.py`, `world/rules/field_contact.py` or `world/maps/population_forecast.py`. With `scope=None` every edited function must behave exactly as before. Tests use synthetic zones, areas and sites only.

## 1. Preconditions

- [ ] 1.1 Confirm `population-settlement-units` is merged: `uv run --locked python -c "from world.maps.population_units import unit_closure, advance_unit_cursors"` exits 0. If not, stop and report.

## 2. Scope and coordinator

- [ ] 2.0 In the new file `world/maps/tests/test_scoped_population_settlement.py`, write the module-level helper `build_two_zone_world(fixture)` of design D5 first (two disjoint synthetic zones, one synthetic site in the first, groups in both) and one smoke test that calls it and asserts both zones are initialized. Register the module in `.github/evennia-shards.json` beside `world.maps.tests.test_population_units`. Verify: the test prefix with `world.maps.tests.test_scoped_population_settlement` passes. If `ActivityFixture`'s registry isolation cannot hold a second zone or a site, stop and report what is missing.
- [ ] 2.1 Add design D1 to `world/maps/population_units.py`. Create `world/maps/tests/test_scoped_population_settlement.py` with `build_scope`, `scope_start_tick` and `behind` assertions for a closed set with equal and with unequal cursors. Verify: the same test label passes.
- [ ] 2.2 Apply design D3 (the `_run_pass` extraction, `settle_population_scope`) with `scope` accepted and passed down but not yet used by the owners. Verify: the test prefix passes for each of `world.maps.tests.test_monster_activity`, `world.maps.tests.test_regional_population_recovery`, `world.maps.tests.test_settlement_decode_reuse`, `world.maps.tests.test_settlement_outer_rollback`, `world.maps.tests.test_settlement_deferred_writes`, `world.maps.tests.test_population_maintenance_log`.

## 3. Owner filters

- [ ] 3.1 Apply design D2 to `world/maps/monster_activity.py`. Add "Other units are untouched", "Cursor moves only for the scope", "Linked units settle together" and "Out-of-scope destination". Verify: the new module passes.
- [ ] 3.2 Apply design D2 to `world/maps/regional_population.py` and `world/maps/monster_sites.py`, and design D4. Add "Loss recorded ahead of one unit", "Protection of a lagging cell", "Reload between parts", "Unequal cursors", "Units linked after diverging", "Group reaching outside the scope" and "Order and partition". Verify: the new module passes, and the test prefix passes for each of `world.maps.tests.test_monster_sites`, `world.maps.tests.test_monster_journeys`, `world.maps.tests.test_regional_population`, `world.rules.tests.test_world_escape`.

## 4. Documentation and gates

- [ ] 4.1 Apply design D6. Verify: `grep -c "PopulationScopeViolation" docs/development/regional-monster-population.md` prints at least 1.
- [ ] 4.2 Run `uv run --locked python -m tools.observability_lint check`, `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.contract_gate --change unit-scoped-population-settlement` and `openspec validate unit-scoped-population-settlement --strict`. Verify: all exit 0.

## Workflow follow-up

- During archive, after the delta sync, annotate the tests of the four ADDED requirements with the identifiers printed by `uv run --locked python -m tools.spec_traceability list`.
