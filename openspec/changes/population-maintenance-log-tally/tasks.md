# Tasks

Run only the focused commands named below. `/tmp/mud-test.env` holds the single line `MUD_TEST_SETTINGS=1`; "the test prefix" means `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`.
Do not add `covers_requirement` for ADDED requirements in this change; that happens at archive.
Do not edit `world/observability/api.py`, `render.py` or `recent.py`. Do not change any event name or context key.

## 1. Tally

- [ ] 1.1 Create `world/observability/tally.py` per design D1 and `world/observability/tests/test_tally.py` per design D4; register the test module in `.github/evennia-shards.json` beside the other `world.observability.tests` modules. Verify: the test prefix with `world.observability.tests.test_tally` passes.

## 2. Emit sites and the pass

- [ ] 2.1 Apply design D2 to the four sites in `world/maps/monster_activity.py` and the one site in `world/rules/fatigue.py`. Verify: `uv run --locked python -m tools.observability_lint check` exits 0.
- [ ] 2.2 Apply design D3 to `world/maps/population_lifecycle.py`. Add `world/maps/tests/test_population_maintenance_log.py` per design D4 and register it in `.github/evennia-shards.json` beside `world.maps.tests.test_monster_activity`. Verify: the test prefix with `world.maps.tests.test_population_maintenance_log` passes.
- [ ] 2.3 Re-run the existing event tests and adjust only as design D4 allows. Verify: the test prefix passes for each of `world.maps.tests.test_monster_activity`, `world.maps.tests.test_monster_journeys`, `world.rules.tests.test_fatigue`, `world.rules.tests.test_world_escape` (one command per module).

## 3. Documentation and gates

- [ ] 3.1 Apply design D5. Verify: `grep -c population_maintenance_settled docs/superpowers/specs/2026-09-02-observability-logging-design.md docs/development/monster-field-behaviour.md` prints at least 1 for each file.
- [ ] 3.2 Run `uv run --locked python -m tools.observability_lint check`, `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.contract_gate --change population-maintenance-log-tally` and `openspec validate population-maintenance-log-tally --strict`. Verify: all exit 0.

## Workflow follow-up

- During archive, after the delta sync, annotate the tests of the two ADDED requirements with the identifiers printed by `uv run --locked python -m tools.spec_traceability list`.
