# Tasks

Run only the focused commands named below. `/tmp/mud-test.env` holds the single line `MUD_TEST_SETTINGS=1`; "the test prefix" means `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`.
Do not add `covers_requirement` for ADDED requirements in this change; that happens at archive.
Do not weaken or bypass the guard to make a test pass. Tests use synthetic zones, areas and sites only.

## 1. Preconditions

- [x] 1.1 Confirm `population-catch-up-entry-points` is merged: `uv run --locked python -c "from world.maps.population_lifecycle import ensure_locations_current; from world.maps.population_units import pass_running, running_pass"` exits 0. If not, stop and report.
  - Note: the literal command cannot bootstrap Django/Evennia outside the test harness (`ImproperlyConfigured`, then `AppRegistryNotReady`); it fails the same way on the baseline. The symbols are proven present by `world.maps.tests.test_population_catch_up`, which imports `ensure_locations_current` and `population_units.pass_running` and passed.

## 2. Guard and writers

- [x] 2.1 Apply design D1 to `world/maps/population_units.py`. Create `world/maps/tests/test_population_writer_guards.py` with direct tests of `require_units_current` (lagging, current, inside `running_pass()`, unprovisioned wilderness) and register it in `.github/evennia-shards.json` beside `world.maps.tests.test_population_catch_up`. Verify: the test prefix with `world.maps.tests.test_population_writer_guards` passes.
- [x] 2.2 Apply design D2 to the five writers. Add the writer tests of design D4. Verify: the same test label passes.

## 3. Existing flows

- [x] 3.1 Run, one command per label: `world.maps.tests.test_monster_activity`, `world.maps.tests.test_monster_journeys`, `world.maps.tests.test_regional_population`, `world.maps.tests.test_regional_population_recovery`, `world.maps.tests.test_monster_sites`, `world.maps.tests.test_population_catch_up`, `world.rules.tests.test_world_escape`. Verify: each passes. A failure with `PopulationUnitNotCurrent` means a test fixture moved the world tick without the cursor record: fix the fixture by writing the record at the same tick; if the failure is in production flow, apply the Non-Goals rule of the design and report it.
- [x] 3.2 Run the test modules of the remaining callers found by `grep -ln "record_population_protection\|commit_monster_departure\|_record_hp_transition\|register_explicit_individual" world/rules/tests/*.py world/quests/tests/*.py` (one command per module, at most eight; list any not run in the hand-off). Verify: each passes.
  - Found two modules: `world.rules.tests.test_world_escape` (passes) and `world.quests.tests.test_permanent_occupants`. The latter cannot run standalone at the baseline: it never publishes the map world and fails with `SettlementNotLoaded` in its own fixture, before any population code. Run with `world.maps.tests.test_monster_activity` in the same process (which publishes the map world, as its shard neighbours do), all 46 tests pass.

## 4. GM view, documentation and gates

- [x] 4.1 Apply design D3 and extend the label test per design D4. Verify: the test prefix with `world.maps.tests.test_monster_activity` passes.
- [x] 4.2 Apply design D5. Verify: `grep -c PopulationUnitNotCurrent docs/development/regional-monster-population.md` prints at least 1.
- [x] 4.3 Run `uv run --locked python -m tools.observability_lint check`, `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.contract_gate --change population-writer-guards` and `openspec validate population-writer-guards --strict`. Verify: all exit 0.

## Workflow follow-up

- During archive, after the delta sync, annotate the tests of the two ADDED requirements with the identifiers printed by `uv run --locked python -m tools.spec_traceability list`.