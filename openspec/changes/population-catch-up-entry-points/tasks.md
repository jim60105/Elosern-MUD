# Tasks

Run only the focused commands named below. `/tmp/mud-test.env` holds the single line `MUD_TEST_SETTINGS=1`; "the test prefix" means `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`.
Do not add `covers_requirement` for ADDED requirements in this change; that happens at archive.
Do not change `settle_population_lifecycle` (the clock stage stays whole-world). Do not add catch-up to any read other than the one named in design D4. Tests use synthetic zones, areas and sites only.

## 1. Preconditions

- [ ] 1.1 Confirm `unit-scoped-population-settlement` is merged: `uv run --locked python -c "from world.maps.population_lifecycle import settle_population_scope; from world.maps.population_units import build_scope; from world.maps.tests.test_scoped_population_settlement import build_two_zone_world"` exits 0. If not, stop and report.

## 2. Catch-up and observed units

- [ ] 2.1 Apply design D1 to `world/rules/clock.py`. Verify: the test prefix passes for `world.rules.tests.test_clock` and for `world.maps.tests.test_settlement_outer_rollback`.
- [ ] 2.2 Apply design D3 and D5 to `world/maps/population_units.py`, and design D2 to `world/maps/population_lifecycle.py`. Create `world/maps/tests/test_population_catch_up.py` with the scenarios of the first two requirements and register it in `.github/evennia-shards.json` beside `world.maps.tests.test_scoped_population_settlement`. Verify: the test prefix with `world.maps.tests.test_population_catch_up` passes.

## 3. Entry points

- [ ] 3.1 Apply design D4 to `commands/command.py`. Add the two command scenarios. Verify: the new module passes, and `uv run --locked python -m tools.observability_lint check` exits 0.
- [ ] 3.2 Apply design D4 to `world/rules/movement_settlement.py`. Add "Movement into a lagging unit". Verify: the new module passes, and the test prefix passes for the movement settlement test module(s) found by `grep -ln "movement_settlement" world/rules/tests/*.py` (one command per module, at most five; if more than five match, run the five whose names contain `movement`).
- [ ] 3.3 Apply design D4 to `world/quests/materializer.py`, `world/maps/gm.py`, `world/rules/gm.py` and `world/quests/runtime.py`. Verify: the test prefix passes for the test modules found by `grep -ln "register_explicit_individual\|site_living_members\|_record_hp_transition" world/quests/tests/*.py world/maps/tests/*.py world/rules/tests/*.py` (one command per module).

## 4. Documentation and gates

- [ ] 4.1 Apply design D7. Verify: `grep -c population_caught_up docs/superpowers/specs/2026-09-02-observability-logging-design.md` prints 1.
- [ ] 4.2 Run `uv run --locked python -m tools.observability_lint check`, `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.contract_gate --change population-catch-up-entry-points` and `openspec validate population-catch-up-entry-points --strict`. Verify: all exit 0.

## Workflow follow-up

- During archive, after the delta sync, annotate the tests of the three ADDED requirements with the identifiers printed by `uv run --locked python -m tools.spec_traceability list`.
