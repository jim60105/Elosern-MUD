# Tasks

Future implementation only. Follow design.md signatures verbatim. Tests use synthetic catalogs only. Run checks with the design.md Verification commands.

## 1. Pure formation rule and publication

- [x] 1.1 Add `MovementUnit` and `movement_units` to `world/lore/monster_activity.py` exactly as design D1 states and export them. In `world/lore/tests/test_monster_activity.py` replace `BindingValidationTests` with `MovementUnitTests` covering: solitary row of 3 → three single-slot units; cohesive mixed rows → one unit with all slots; two different cohesive keys → two units; stationary row of 2 → two units; zero-count row skipped; length mismatch, bool/negative count and unknown binding raise `MonsterActivityRegistryError`. Annotate the formation cases with the added requirement ID. Check: `uv run --locked python -m unittest world.lore.tests.test_monster_activity` passes.
- [x] 1.2 Delete `validate_activity_binding` (design D2) and its calls in `world/lore/monster_placement.py`; keep the unknown-reference checks. In `world/lore/tests/test_monster_placement.py` replace `test_a_solitary_site_override_must_fit_every_composition_outcome` with a test that publishes a site whose solitary override covers a two-member composition, and keep an unknown-activity rejection case. Check: focused label `world.lore.tests.test_monster_placement` passes and `grep -rn validate_activity_binding world` returns nothing.

## 2. Writers

- [x] 2.1 Implement design D3 in `commit_population_wave`. Extend `world/maps/tests/test_regional_population.py` with synthetic zones: a solitary 3-member birth creates three groups `wave:<zone>:<seq>#0..2` at the birth cell; a cohesive mixed birth creates one; a fault injected into the second `create_group` call restores individuals, groups, zone state and room `contents_cache`, and a retry commits the same selection. Check: the new test class passes under the focused command.
- [x] 2.2 Add `register_explicit_group` and make `register_explicit_individual` delegate (design D4); update `monster_sites._populate`. Extend `world/maps/tests/test_monster_sites.py`: a synthetic three-member site under a cohesive override creates one group owned by the site; under a stationary override three groups; a fault in the second unit's registration restores site state and every member; quest/GM single registration keeps group id `explicit:x:y:pk#0` and transition `source_id` `explicit:x:y:pk`, so every existing assertion in `world/quests/tests` and `world/maps/tests/test_gm*.py` reading those values passes unchanged. Check: focused classes in `world.maps.tests.test_monster_sites` and `world.maps.tests.test_regional_population` pass.

## 3. Forecast and documentation

- [x] 3.1 Implement design D5 in `world/maps/population_forecast.py`. Extend `world/rules/tests/test_field_contact_boundaries.py` with a synthetic solitary multi-member zone birth and a matured cohesive site recovery whose projected group count and member counts equal the committed writer's result for the same saved seed and sequence. Check: the new tests pass under the focused command.
- [x] 3.2 Add the section "Activity Group Formation" to `docs/development/monster-field-behaviour.md` (rule, writer/forecast parity, removed solitary-total check, new site group id prefix, evidence map from requirement scenarios to test methods) and correct the "Declaration schema" text that says a solitary binding must total one, plus the two references to the removed `BindingValidationTests.test_solitary_binding_rejects_any_multi_individual_outcome` (the prose near line 241 and the evidence-table row near line 294 of `docs/development/monster-field-behaviour.md`), repointing them to `MovementUnitTests`. Regenerate `content/map-reference-context.json`. Check: `uv run --locked python -m tools.map_reference_context --check` exits 0.

## 4. Handoff

- [x] 4.1 Run the focused labels touched above, `uv run --locked python -m tools.observability_lint check`, `openspec validate activity-group-formation --strict` and `uv run --locked python -m tools.contract_gate`; record exact commands and results in the new developer section. Check: every command exits 0, no new test module was added (so `.github/evennia-shards.json` is unchanged), and no unexecuted check is reported as passed.
