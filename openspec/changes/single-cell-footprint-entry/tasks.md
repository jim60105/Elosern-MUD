# Tasks

Test prefix: `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`
(`/tmp/mud-test.env` contains the single line `MUD_TEST_SETTINGS=1`; create it if missing).
Run only the focused labels named below, one command per label. Never run a whole test suite for this change.
Do not add `covers_requirement` for the ADDED requirements (design D4).

## 1. Map core

- [ ] 1.1 Add the schema field of design D1 and the field, property and plumbing of design D2 in `packages/map-core/elosern_map_core/schema.py` and `documents.py`. Add the first, second and fourth map-core tests of design D4 to `packages/map-core/tests/test_authoring.py`. Verify: from `packages/map-core`, `uv run --locked --extra generation python -m pytest tests/test_authoring.py -q` passes.
- [ ] 1.2 Add the `single_cell_footprint_mask` diagnostic of design D3 in `authoring.py` and its test. Verify: the same pytest command passes, and `uv run --locked --project packages/map-core python .agents/skills/map-data-authoring/scripts/check_map_sources.py` exits 0 on the shipped sources.

## 2. Game side

- [ ] 2.1 Add the field and property to `WildernessEntryPoint` in `world/lore/wilderness_entry.py` and pass it in `world/maps/map_data.py` (design D2). Add the two game tests of design D4. Verify: the test prefix on `world.lore.tests.test_wilderness_entry` and on `world.maps.tests.test_wilderness_destination` passes.
- [ ] 2.2 Run the test prefix on `world.maps.tests.test_wilderness_provider` and `world.maps.tests.test_population_geometry`. Verify: both pass with no edit, which shows that unflagged entries are unchanged.

## 3. Lint and documentation

- [ ] 3.1 Add the lint test of design D4 to `tests/test_settlement_terrain_fit.py`. Verify: `uv run --locked python -m unittest tests.test_settlement_terrain_fit` passes with no change to `tools/settlement_synthesis/fit_lint.py`. If the new test fails, stop and report; do not special-case the lint.
- [ ] 3.2 Apply the documentation edits of design D5. Verify: `grep -c 'single_cell_footprint' .agents/skills/map-data-authoring/references/settlements.md docs/development/map-authoring-documents.md` shows at least 1 for each file.

## 4. Gates

- [ ] 4.1 After the last source edit, run `uv run --locked python -m tools.map_reference_context`. Verify: the same command with `--check` exits 0, and `uv run --locked python -m tools.road_network --check` exits 0 without regeneration.
- [ ] 4.2 Run `uv run --locked python -m tools.observability_lint check`, `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.contract_gate --change single-cell-footprint-entry` and `openspec validate single-cell-footprint-entry --strict`. Verify: all exit 0. The hand-off lists each new test with the delta requirement and scenario it establishes.

## Workflow follow-up

- During archive, after the delta sync, annotate the tests of the two ADDED requirements with the identifiers printed by `uv run --locked python -m tools.spec_traceability list`.
