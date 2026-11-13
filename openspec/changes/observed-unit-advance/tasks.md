# Tasks

Run only the focused commands named below. `/tmp/mud-test.env` holds the single line `MUD_TEST_SETTINGS=1`; "the test prefix" means `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`.
Do not add `covers_requirement` for ADDED requirements in this change; that happens at archive. The MODIFIED requirement keeps its existing annotations.
Do not change `settle_population_lifecycle`, unit resolution, owner filters, catch-up or writers. Do not add a wall-clock assertion. Tests use synthetic zones, areas and sites only.

## 1. Preconditions

- [ ] 1.1 Confirm `population-writer-guards` is merged: `uv run --locked python -c "from world.maps.population_lifecycle import ensure_population_current; from world.maps.population_units import observed_units, require_current; from world.maps.tests.test_population_catch_up import place_player"` exits 0. If not, stop and report.

## 2. Observed pass

- [ ] 2.1 Add `catch_up_world` to `world/maps/tests/_settlement_projection.py` (design D4). Apply design D2 (registry contract). Verify: the test prefix passes for each of `world.maps.tests.test_scoped_population_settlement`, `world.maps.tests.test_population_catch_up`.
- [ ] 2.2 Apply design D1 (`settle_observed_population`, registration) and D3 (forecast). Create `world/maps/tests/test_observed_unit_advance.py` per design D4 and register it in `.github/evennia-shards.json` beside `world.maps.tests.test_population_catch_up`. Verify: the test prefix with `world.maps.tests.test_observed_unit_advance` passes.

## 3. Existing tests (design D5)

- [ ] 3.1 Run and fix per design D5, one command per label: `world.maps.tests.test_monster_activity`, `world.maps.tests.test_monster_journeys`, `world.maps.tests.test_monster_sites`, `world.maps.tests.test_regional_population`, `world.maps.tests.test_regional_population_recovery`, `world.maps.tests.test_population_zone_pass`, `world.maps.tests.test_wilderness_population`. Verify: each passes.
- [ ] 3.2 Run and fix per design D5, one command per label: `world.maps.tests.test_settlement_outer_rollback`, `world.maps.tests.test_settlement_deferred_writes`, `world.maps.tests.test_population_maintenance_log`, `world.rules.tests.test_world_escape`, `world.rules.tests.test_clock`, `world.rules.tests.test_fatigue`. Verify: each passes.
- [ ] 3.3 Find the remaining callers of the stage: `grep -rln "register_regional_population\|_register_lifecycle\|next_population_lifecycle_boundary" --include='*.py' world commands server web | grep tests`. Run each module not already run in 3.1 or 3.2 (one command per module) and fix per design D5. Verify: each passes. List in the hand-off every test changed and which D5 rule applied.

## 4. Documentation, amendments and gates

- [ ] 4.1 Apply design D6. Verify: `grep -c "change observed-unit-advance" docs/superpowers/specs/2026-11-03-monster-field-behaviour-and-escape-design.md` prints 2, and the same grep prints 1 for `docs/superpowers/specs/2026-11-03-regional-monster-population-design.md` and for `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md`.
- [ ] 4.2 Run `uv run --locked python -m tools.observability_lint check`, `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.contract_gate --change observed-unit-advance` and `openspec validate observed-unit-advance --strict`. Verify: all exit 0.
- [ ] 4.3 Information only, never a gate: if a profiling database copy is available, record in the hand-off the wall time and SQL statement count of one 3,580 second `clock.advance(seconds, AdvanceSource.COMMAND, [])` before and after this change. Skip without failing when no copy is available.

## Workflow follow-up

- During archive, after the delta sync, annotate the tests of the four ADDED requirements with the identifiers printed by `uv run --locked python -m tools.spec_traceability list`.
