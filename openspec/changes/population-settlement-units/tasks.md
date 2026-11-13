# Tasks

Run only the focused commands named below. `/tmp/mud-test.env` holds the single line `MUD_TEST_SETTINGS=1`; "the test prefix" means `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`.
Do not add `covers_requirement` for ADDED requirements in this change; that happens at archive.
Do not change which groups, zones or sites a pass settles. Tests use synthetic zones, areas and sites only.

## 1. Preconditions

- [ ] 1.1 Confirm `settlement-deferred-body-writes` is merged: `uv run --locked python -c "from world.rules.surfaces import store_attribute"` exits 0. If not, stop and report.

## 2. Unit index

- [ ] 2.1 Create `world/maps/population_units.py` with design D1. Create `world/maps/tests/test_population_units.py` with the D1 tests (including "Birth binding links a zone to a distant area" with a hand-built `bound_areas` mapping, and one test of `zone_bound_areas()` over the fixture's synthetic registries) and register it in `.github/evennia-shards.json` beside `world.maps.tests.test_population_zone_pass`. Verify: the test prefix with `world.maps.tests.test_population_units` passes.
- [ ] 2.2 Add design D2 and D3 (including `regional_population.cell_region` and the public `monster_activity.group_area`). Add their tests. Verify: the same test label passes.
- [ ] 2.3 Information only: run `uv run --locked python -c "import os, django; os.environ['DJANGO_SETTINGS_MODULE']='server.conf.settings'; django.setup(); from world.maps.population_units import current_unit_index; i=current_unit_index(); print(len(set(i.unit_of_zone.values())))"` and record the printed unit count in the hand-off.

## 3. Cursor record

- [ ] 3.1 Add design D4 to `world/maps/population_units.py`, `world/maps/regional_population.py` and `world/maps/population_lifecycle.py`. Add the scenarios "Fresh world", "Pass records its endpoint", "Rollback" and "Malformed record". Verify: the same test label passes, and the test prefix passes for each of `world.maps.tests.test_regional_population`, `world.maps.tests.test_monster_activity`, `world.maps.tests.test_settlement_deferred_writes`.
- [ ] 3.2 Apply design D5 to every hand-provisioning fixture the grep finds. Verify: the test prefix passes for each test module the grep lists (one command per module; if more than eight modules are listed, run the eight under `world/maps/tests` and `world/rules/tests` first and list the rest in the hand-off as not run).

## 4. Documentation and gates

- [ ] 4.1 Apply design D7. Verify: `grep -c "Settlement units" docs/development/regional-monster-population.md` prints at least 1.
- [ ] 4.2 Run `uv run --locked python -m tools.observability_lint check`, `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.contract_gate --change population-settlement-units` and `openspec validate population-settlement-units --strict`. Verify: all exit 0.

## Workflow follow-up

- During archive, after the delta sync, annotate the tests of the three ADDED requirements with the identifiers printed by `uv run --locked python -m tools.spec_traceability list`.
