# Tasks

Follow design.md verbatim. No other module changes.

## 1. Readers

- [ ] 1.1 In `world/maps/regional_population.py` add `_zone_state_from_record`, `zone_states`, `due_recovery_zone_keys` and `zone_counts_from_presence`, and re-point `zone_state` and `counts_from_presence` to them (design D1). Check: `world.maps.tests.test_regional_population` passes unchanged.
- [ ] 1.2 Split `_boundary_fields` into `_boundary_fields_from` plus the wrapper, and rewrite `note_population_boundaries` (design D2). Check: `world.maps.tests.test_regional_population_recovery` passes unchanged.

## 2. Callers

- [ ] 2.1 In `world/maps/population_lifecycle.py`, iterate `due_recovery_zone_keys` in `_settle_population_at` and `zone_states` in `_next_population_boundary` (design D3). Check: `world.maps.tests.test_monster_activity` passes unchanged.
- [ ] 2.2 In `world/maps/population_forecast.py`, use `zone_states` in `capture_activity_snapshot` and one batch count in `_Projection._note_zone_boundary` (design D4). Check: `world.rules.tests.test_field_contact_boundaries` passes unchanged.

## 3. Tests

- [ ] 3.1 Add `world/maps/tests/test_population_zone_pass.py` with the three classes and six tests of design D5, and register the label once in shard `maps-34-6` of `.github/evennia-shards.json`. Check: the module passes, and each count assertion fails when the matching D1–D4 edit is reverted locally (revert, run, restore; record the observation in the handoff report).

## 4. Handoff

- [ ] 4.1 Run every label in design.md Verification, `uv run --locked python -m tools.contract_gate --change population-zone-pass-indexing` and `openspec validate population-zone-pass-indexing --strict`. Check: all exit 0. The report lists the test-to-requirement handoff (the four scenarios of the ADDED requirement and the tests that establish each one) with no `covers_requirement` annotation added before archive sync.
