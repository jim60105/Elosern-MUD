# Tasks

Test prefix: `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`.

## 1. Record and hooks

- [x] 1.1 Create `world/rules/scene_visits.py` per design D1 and add the two hook calls of design D3 in `typeclasses/rooms.py`. Verify `uv run --locked python -m tools.observability_lint check` passes.
- [x] 1.2 Create `world/rules/tests/test_scene_visits.py` (`EvenniaTest`, synthetic archetypes, grid and instance rooms moved into with `move_to`) with one test per ADDED scenario; the delta's ADDED requirements have no canonical ID before archive sync, so the tests stay unannotated until then (`docs/development/spec-test-traceability.md`) and the change report carries the test → requirement/scenario hand-off. Register it in `.github/evennia-shards.json`. Verify `<prefix> world.rules.tests.test_scene_visits tests.test_evennia_test_optimization_contract` passes.

## 2. Gates

- [x] 2.1 Run `uv run --locked python -m tools.spec_traceability check`, `uv run --locked python -m tools.test_data_lint check` and `uv run --locked python -m tools.contract_gate --change entered-archetype-record`; all pass.
- [x] 2.2 Run `openspec validate entered-archetype-record --strict`; it passes.
