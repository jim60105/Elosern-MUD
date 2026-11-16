# Tasks

"The test prefix" means `uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb`. Run each test command standalone (no pipe, no redirect), with one dotted label.
Do not add `covers_requirement` for the ADDED requirements of this change; that happens at archive.
No test may sleep, start a timer or assert elapsed real time. A test controls time only by patching `world.rules.player_input._now` with fixed values.
Do not edit `drain_population_backlog`, `world/maps/population_units.py`, `world/maps/population_lifecycle.py` or any owner module.

## 1. Input record

- [ ] 1.1 Create `world/rules/player_input.py` exactly as design D1. Verify: `uv run --locked python -c "import world.rules.player_input as m; print(sorted(m.__all__))"` prints `['note_player_input', 'reset_player_input', 'seconds_since_player_input']`.
- [ ] 1.2 Create `world/rules/tests/test_player_input.py` (a plain `unittest.TestCase`; `setUp` and `tearDown` call `reset_player_input()`), with three tests that patch `world.rules.player_input._now`: no input recorded answers `None`; after `note_player_input()` at reading 100.0 a read at 102.5 answers 2.5; `reset_player_input()` answers `None` again. Then run `uv run --locked python -m tools.shard_register fix` (do not edit `.github/evennia-shards.json` by hand). Verify: the test prefix with `world.rules.tests.test_player_input` passes and `uv run --locked python -m tools.contract_gate manifests contracts` exits 0.

## 2. Ingress

- [ ] 2.1 Apply design D2 to `server/conf/inputfuncs.py`. Verify: `grep -c "note_player_input" server/conf/inputfuncs.py` prints 3 (one import, two calls).
- [ ] 2.2 In `server/conf/tests/test_inputfuncs.py` add one test class whose `setUp` and `tearDown` call `reset_player_input()` and which covers the four scenarios of the requirement "Player input is recorded at command and action ingress", reusing that module's existing session doubles and patches: a non-idle `text` records (`seconds_since_player_input()` is not `None`); the idle keepalive does not; `ui_action` from a WebClient session with a puppet records (patch `server.conf.inputfuncs.handle_ui_action`); `ui_sync` and a `ui_action` with `session.puppet = None` do not. Verify: the test prefix with `server.conf.tests.test_inputfuncs` passes.

## 3. Gate and setting

- [ ] 3.1 Apply design D4 to `server/conf/settings.py`, `server/conf/test_settings.py`, `.env.example` and `server/conf/tests/test_env_overrides/_support.py`. Verify: the test prefix with `server.conf.tests.test_env_overrides` passes.
- [ ] 3.2 Apply design D3 to `world/maps/population_drain.py`. In `world/maps/tests/test_population_drain.py`: make `DrainFixture.setUp` call `player_input.reset_player_input()` and register `self.addCleanup(player_input.reset_player_input)`; add to `PeriodicCallerTests` the three scenarios of "The periodic drain yields to recent player input" (patch `world.rules.player_input._now` to return 100.0 for `note_player_input()` and then 102.0 or 105.0 for the repeat, with `override_settings(POPULATION_DRAIN_ENABLED=True, POPULATION_DRAIN_IDLE_SECONDS=5)`; assert the wrapped `drain_population_backlog` call count and the unit's settled-through tick, following `test_disabled_repeat_does_not_drain`; in the recent-input test also patch `world.maps.population_units.lagging_sets` and `world.maps.monster_activity.read_monster_activity` with `wraps=` and `world.maps.population_drain.log_info` and assert none was called); add a class `IdleWindowBypassTests(DrainFixture)` with the two scenarios of "Catch-up and direct drains ignore the idle window" (call `note_player_input()` first, then `population_lifecycle.ensure_population_current(self.wilderness, {self.unit_a})` in one test and `self.drain()` in the other). Verify: the test prefix with `world.maps.tests.test_population_drain` passes.
- [ ] 3.3 Apply design D5 to both documents. Verify: `grep -c POPULATION_DRAIN_IDLE_SECONDS docs/development/settings-and-environment.md` and the same command on `docs/development/regional-monster-population.md` each print 1 or more.

## 4. Gates

- [ ] 4.1 Run `uv run --locked python -m tools.observability_lint check`, `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.contract_gate` and `openspec validate population-drain-idle-gate --strict`. Verify: all exit 0.

## Workflow follow-up

- During archive, after the delta sync, annotate the tests of the three ADDED requirements with the identifiers printed by `uv run --locked python -m tools.spec_traceability list`.
