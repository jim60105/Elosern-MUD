# Tasks

Test prefix: `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`.

## 1. Module

- [x] 1.1 Create `world/rules/met_people.py` with exactly the storage and API of design D1–D3. Verify `uv run --locked python -m tools.observability_lint check` passes.

## 2. Tests

- [x] 2.1 Create `world/rules/tests/test_met_people.py` (`EvenniaTest`; the synthetic grid map from `world/tests/synthetic_grid_map.py` registered as a synthetic settlement graph, a `TerrainRoom` at a synthetic region cell via `world/tests/geography_fixture.py`, synthetic named and generic NPCs) with one test per scenario of `specs/met-person-record/spec.md`; the ADDED requirements have no canonical ID before archive sync, so the tests stay unannotated until then (`docs/development/spec-test-traceability.md`), and the change report carries the test → requirement/scenario hand-off. Register the module in `.github/evennia-shards.json`. Verify `<prefix> world.rules.tests.test_met_people tests.test_evennia_test_optimization_contract` passes.

## 3. Gates

- [x] 3.1 Run `uv run --locked python -m tools.spec_traceability check`, `uv run --locked python -m tools.test_data_lint check` and `uv run --locked python -m tools.contract_gate --change met-person-record`; all pass.
- [x] 3.2 Run `openspec validate met-person-record --strict`; it passes.
