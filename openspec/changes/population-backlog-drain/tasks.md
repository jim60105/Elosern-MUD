# Tasks

Run only the focused commands named below. `/tmp/mud-test.env` holds the single line `MUD_TEST_SETTINGS=1`; "the test prefix" means `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`.
Do not add `covers_requirement` for ADDED requirements in this change; that happens at archive.
Do not change the clock stage, catch-up, entry points or owners. No test may start a timer, sleep, or measure time. Tests use synthetic zones, areas and sites only.

## 1. Preconditions

- [ ] 1.1 Confirm `observed-unit-read-narrowing` is merged (and with it `observed-unit-advance`): `uv run --locked python -c "from world.maps.population_lifecycle import settle_observed_population; from world.maps.tests._settlement_projection import catch_up_world"` exits 0. If not, stop and report.

## 2. Drain

- [ ] 2.1 Apply design D1 to `world/maps/population_units.py`. Verify: the test prefix with `world.maps.tests.test_population_units` passes.
- [ ] 2.2 Create `world/maps/population_drain.py` with design D2. Create `world/maps/tests/test_population_drain.py` with the scenarios of the first three requirements and register it in `.github/evennia-shards.json` beside `world.maps.tests.test_observed_unit_advance`. Verify: the test prefix with `world.maps.tests.test_population_drain` passes.

## 3. Periodic caller and settings

- [ ] 3.1 Apply design D4 to `server/conf/settings.py`, `server/conf/test_settings.py` and `.env.example`. Verify: the test prefix with `server.conf.tests.test_env_overrides` passes.
- [ ] 3.2 Apply design D3. Add the two scenarios of the fourth requirement. Verify: the test prefix with `world.maps.tests.test_population_drain` passes, and `uv run --locked python -c "import os, django; os.environ['DJANGO_SETTINGS_MODULE']='server.conf.settings'; django.setup(); from django.conf import settings; from django.utils.module_loading import import_string; import_string(settings.GLOBAL_SCRIPTS['population_drain']['typeclass'])"` exits 0.

## 4. Documentation and gates

- [ ] 4.1 Apply design D6 and the settings table entry of design D4. Verify: `grep -c POPULATION_DRAIN docs/development/settings-and-environment.md` prints at least 3, and `grep -c "change population-backlog-drain" docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` prints 1.
- [ ] 4.2 Run `uv run --locked python -m tools.observability_lint check`, `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.contract_gate --change population-backlog-drain` and `openspec validate population-backlog-drain --strict`. Verify: all exit 0.
- [ ] 4.3 Manual check, recorded in the hand-off as information only: start the server with `scripts/serve.sh` on a world with a lagging unit, confirm one `population_backlog_drained` line appears in `server/logs/server.log`, stop the server.

## Workflow follow-up

- During archive, after the delta sync, annotate the tests of the four ADDED requirements with the identifiers printed by `uv run --locked python -m tools.spec_traceability list`.
