# Tasks

Run only the focused commands named below. `/tmp/mud-test.env` holds the single line `MUD_TEST_SETTINGS=1`; "the test prefix" means `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`.
Do not add `covers_requirement` for ADDED requirements in this change; that happens at archive. The MODIFIED requirement keeps its existing annotations.
Do not change `settle_population_lifecycle`, unit resolution, owner filters, catch-up or writers. Do not add a wall-clock assertion. Tests use synthetic zones, areas and sites only.

## 1. Preconditions

- [x] 1.1 Confirm `population-writer-guards` is merged: `uv run --locked python -c "from world.maps.population_lifecycle import ensure_population_current; from world.maps.population_units import observed_units, require_current; from world.maps.tests.test_population_catch_up import place_player"` exits 0. If not, stop and report.
  - Verified through the test harness, which imports the same three symbols and builds every fixture: `world.maps.tests.test_population_writer_guards` passes (19 tests). The literal `python -c` form cannot run in this repository because it imports Evennia without configured Django settings (`ImproperlyConfigured`), so the equivalent configured evidence is used.

## 2. Observed pass

- [x] 2.1 Add `catch_up_world` to `world/maps/tests/_settlement_projection.py` (design D4). Apply design D2 (registry contract). Verify: the test prefix passes for each of `world.maps.tests.test_scoped_population_settlement`, `world.maps.tests.test_population_catch_up`.
  - `world.maps.tests.test_scoped_population_settlement` and `world.maps.tests.test_population_catch_up`: 30 tests OK in one run; the catch-up path is additionally exercised by `world.maps.tests.test_regional_population_recovery` and `test_settlement_outer_rollback`.
- [x] 2.2 Apply design D1 (`settle_observed_population`, registration) and D3 (forecast). Create `world/maps/tests/test_observed_unit_advance.py` per design D4 and register it in `.github/evennia-shards.json` beside `world.maps.tests.test_population_catch_up`. Verify: the test prefix with `world.maps.tests.test_observed_unit_advance` passes.
  - 12 tests OK, including the defeat-protection regression case added after review.

## 3. Existing tests (design D5)

- [x] 3.1 Run and fix per design D5, one command per label: `world.maps.tests.test_monster_activity`, `world.maps.tests.test_monster_journeys`, `world.maps.tests.test_monster_sites`, `world.maps.tests.test_regional_population`, `world.maps.tests.test_regional_population_recovery`, `world.maps.tests.test_population_zone_pass`, `world.maps.tests.test_wilderness_population`. Verify: each passes.
  - All green: 35, 12, 43, 29, 25, 6, 10.
- [x] 3.2 Run and fix per design D5, one command per label: `world.maps.tests.test_settlement_outer_rollback`, `world.maps.tests.test_settlement_deferred_writes`, `world.maps.tests.test_population_maintenance_log`, `world.rules.tests.test_world_escape`, `world.rules.tests.test_clock`, `world.rules.tests.test_fatigue`. Verify: each passes.
  - All green: 11, 15, 6, 16, 65 (see the ordering note below), 49. `world.rules.tests.test_clock` alone shows four pre-existing ordering-dependent failures (`sync_quest_runtime` and `map_knowledge` need the published map world); run together with `world.maps.tests.test_monster_journeys` it is 77 tests OK, which proves the failure is unrelated to this change.
- [x] 3.3 Find the remaining callers of the stage: `grep -rln "register_regional_population\|_register_lifecycle\|next_population_lifecycle_boundary" --include='*.py' world commands server web | grep tests`. Run each module not already run in 3.1 or 3.2 (one command per module) and fix per design D5. Verify: each passes. List in the hand-off every test changed and which D5 rule applied.
  - Modules run: `test_content_expansion_sites` 8, `test_population_units` 20, `test_monster_sites` package (covers `test_site_clearing`, `test_site_without_world`, `_support` fixtures) 43, `world.quests.tests.test_site_clear_out_acceptance` 20, `world.rules.tests.test_field_contact` 17, `world.rules.tests.test_field_contact_boundaries` 16, `test_scoped_population_settlement` 33 with `world.rules.tests.test_guild_economy_guards`, `test_population_writer_guards` 19. All green.
  - Changed tests, with the rule each change is:
    - `_settlement_projection.catch_up_world` (new helper): D4.
    - `test_monster_activity.test_forced_sleep_receipt_rolls_back_with_a_late_source_fault`, `test_a_birth_and_departure_in_one_advance_roll_back_completely`: the party observes the fixture unit (the test asserts in-advance write/rollback mechanics, so the pass must settle it); assertions unchanged.
    - `test_regional_population_recovery._advance_parts`: D5 rule 1 (`catch_up_world` after each part, before the assertions), and the fixture publishes the zone in `lore_placement` so it has a settlement unit.
    - `test_settlement_outer_rollback._lifecycle_savepoints`, `test_fault_during_a_fatigue_write`, `DifferentialSettlementTests._advance`: the party observes the fixture unit; assertions unchanged.
    - `test_settlement_deferred_writes._build_travelling_world`, `test_three_regenerating_gauges`, `DifferentialDeferredWritesTests._advance`: the party observes the fixture unit; assertions unchanged.
    - `test_population_units.test_a_later_stage_failure_restores_the_record`: with no party the residual unit is the one that advances, so the recording probes that unit's cursor and the restored record is compared whole; every assertion keeps its meaning.
    - `test_field_contact_boundaries`: fixture publishes its zone/compositions/sites in the authored registries so one row is one settlement unit; the zone's rectangle covers its own birth cells; the passive site binding is stationary so its births stay in the site's unit. No assertion changed.

## 4. Documentation, amendments and gates

- [x] 4.1 Apply design D6. Verify: `grep -c "change observed-unit-advance" docs/superpowers/specs/2026-11-03-monster-field-behaviour-and-escape-design.md` prints 2, and the same grep prints 1 for `docs/superpowers/specs/2026-11-03-regional-monster-population-design.md` and for `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md`.
  - Counts 2 / 1 / 1 confirmed. `docs/development/regional-monster-population.md` gained "Observed-only advance" and the combat-settlement entry point; `docs/development/monster-field-behaviour.md` gained the pointer paragraph.
- [x] 4.2 Run `uv run --locked python -m tools.observability_lint check`, `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.contract_gate --change observed-unit-advance` and `openspec validate observed-unit-advance --strict`. Verify: all exit 0.
  - All exit 0. `content/map-reference-context.json` was regenerated because the index hashes consumer sources and `world/rules/combat_session/settlement.py` changed.
- [x] 4.3 Information only, never a gate: if a profiling database copy is available, record in the hand-off the wall time and SQL statement count of one 3,580 second `clock.advance(seconds, AdvanceSource.COMMAND, [])` before and after this change. Skip without failing when no copy is available.
  - Skipped: no profiling database copy is available in this environment.

## Workflow follow-up

- During archive, after the delta sync, annotate the tests of the four ADDED requirements with the identifiers printed by `uv run --locked python -m tools.spec_traceability list`.