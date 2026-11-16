# Tasks

"The test prefix" means `uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb`. Run each test command standalone (no pipe, no redirect), with one dotted label; when a label discovers more than 100 tests, run its classes or submodules separately.
This change adds no requirement and no test. Do not change any assertion's meaning, any production caller, or the stored form.

## 1. Owner functions

- [ ] 1.1 Apply design D1 to `world/maps/monster_activity.py`. Verify: `uv run --locked python -c "import ast,sys; t=ast.parse(open('world/maps/monster_activity.py').read()); n={f.name for f in t.body if isinstance(f, ast.FunctionDef)}; sys.exit(0 if {'read_stored_monster_activity','write_monster_activity'} <= n else 1)"` exits 0, and the test prefix with `world.maps.tests.test_monster_activity` passes.

## 2. Tests

- [ ] 2.1 Apply the rules of design D2 to `world/maps/tests/test_monster_activity.py`, `world/maps/tests/test_monster_journeys.py`, `world/maps/tests/test_population_drain.py`, `world/maps/tests/test_population_units.py` and `world/maps/tests/test_settlement_outer_rollback.py`, leaving the statements of design D3. Verify: the test prefix passes for each of those five modules (one command per label).
- [ ] 2.2 Apply the rules of design D2 to `world/maps/tests/test_regional_population.py`, `world/maps/tests/test_monster_sites/test_site_population.py` and `world/rules/tests/test_field_contact_boundaries.py`. Verify: the test prefix passes for `world.maps.tests.test_regional_population`, `world.maps.tests.test_monster_sites.test_site_population` and `world.rules.tests.test_field_contact_boundaries`.
- [ ] 2.3 Run `grep -rn "db\.monster_activity" --include="*.py" world server web commands typeclasses`. Verify: the only hits outside `world/maps/monster_activity.py` are the statements design D3 keeps (the malformed-record test of `test_monster_journeys.py` and the `["settled_through_tick"] = 777` line of `test_monster_activity.py`); list them in the hand-off.

## 3. Gates

- [ ] 3.1 Run `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.contract_gate` and `openspec validate monster-activity-record-access --strict`. Verify: all exit 0.
