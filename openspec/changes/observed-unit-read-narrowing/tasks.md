# Tasks

Run only the focused commands named below. `/tmp/mud-test.env` holds the single line `MUD_TEST_SETTINGS=1`; "the test prefix" means `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`.
Do not add `covers_requirement` for ADDED requirements in this change; that happens at archive.
Do not change `_living_monsters`, the forecast or any stored format. Do not add a wall-clock assertion. Tests use synthetic zones, areas and sites only.

## 1. Preconditions

- [ ] 1.1 Confirm `observed-unit-advance` is merged: `uv run --locked python -c "from world.maps.population_lifecycle import settle_observed_population; from world.maps.tests._settlement_projection import catch_up_world"` exits 0. If not, stop and report.

## 2. Scoped enumeration

- [ ] 2.1 Apply design D1. Create `world/maps/tests/test_observed_unit_read_narrowing.py` with the four scenarios of the first requirement (design D3) and register it in `.github/evennia-shards.json` beside `world.maps.tests.test_observed_unit_advance`. Verify: the test prefix with `world.maps.tests.test_observed_unit_read_narrowing` passes.
- [ ] 2.2 Add the scenario "Growing the far zone". Verify: the same test label passes. If it fails, follow the first risk of the design.
- [ ] 2.3 Verify the neighbours, one command per label: `world.maps.tests.test_observed_unit_advance`, `world.maps.tests.test_scoped_population_settlement`, `world.maps.tests.test_population_catch_up`, `world.maps.tests.test_settlement_decode_reuse`, `world.maps.tests.test_regional_population_recovery`, `world.maps.tests.test_population_zone_pass`.

## 3. Documentation and gates

- [ ] 3.1 Apply design D4. Verify: `grep -c "_scope_living_monsters\|scoped enumeration" docs/development/regional-monster-population.md` prints at least 1.
- [ ] 3.2 Run `uv run --locked python -m tools.observability_lint check`, `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.contract_gate --change observed-unit-read-narrowing` and `openspec validate observed-unit-read-narrowing --strict`. Verify: all exit 0.

## Workflow follow-up

- During archive, after the delta sync, annotate the tests of the two ADDED requirements with the identifiers printed by `uv run --locked python -m tools.spec_traceability list`.
