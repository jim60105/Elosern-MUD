# Tasks

Run only the focused commands named below. `/tmp/mud-test.env` holds the single line `MUD_TEST_SETTINGS=1`; "the test prefix" means `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`.
Do not add `covers_requirement` for ADDED requirements in this change; that happens at archive. A test annotated for a REMOVED requirement keeps its annotation until archive.
Do not touch the `district_lit` flag, the `lit_district` notice field, `LandmarkCard.vue` or any browser file.

## 1. Preconditions

- [x] 1.1 Confirm `landmark-rite-stage` is merged (the browser can perform a rite): `ls web/webclient-app/composables/use-rite-stage.js web/webclient/presentation/rite.py world/rules/landmark_rite_record.py` lists three files. If not, stop and report.

## 2. Lit set

- [x] 2.1 Apply design D1 to `world/rules/map_district_lighting.py`, add the helper `complete_rite_record`, and rewrite `world/rules/tests/test_map_district_lighting.py` per design D6. Verify: the test prefix with `world.rules.tests.test_map_district_lighting` passes.
- [x] 2.2 Apply design D2 to `world/rules/map_knowledge.py` and update `world/rules/tests/test_ground_reveal.py` per design D6. Verify: the test prefix with `world.rules.tests.test_ground_reveal` passes.
- [x] 2.3 Apply design D3 to `sight.py`, `travel_events.py`, `travel_interrupts.py`, `area_map.py`, `world_map.py`, `tools/world_map_payload.py` and `rite.py`, and update the world map, area map and rite panel tests per design D6. Verify: `grep -rn "lit_district_keys_from_visits\|_lit_district_keys_for_record\|\.lit_district_keys()" world web typeclasses commands tools --include=*.py` prints nothing, and the test prefix passes for each of `web.webclient.presentation.tests.test_world_map`, `web.webclient.presentation.tests.test_world_map_measurement`, `web.webclient.presentation.tests.test_area_map`, `web.webclient.presentation.tests.test_rite_panel` (four commands).

## 3. Movement narrative

- [x] 3.1 Apply design D4 and update `typeclasses/tests/test_map_discovery.py` and `world/rules/tests/test_landmark_rites.py` per design D6. Verify: the test prefix passes for `typeclasses.tests.test_map_discovery` and for `world.rules.tests.test_landmark_rites` (two commands).

## 4. Remaining consumers' tests

- [ ] 4.1 Run the inventory grep of design D6, convert each visit-lit fixture to `complete_rite_record`, and run each affected module as its own command (a `tests/` module with `uv run --locked python -m unittest <module>`, others with the test prefix). Verify: each passes; name every converted module in the hand-off.

## 5. Documentation and gates

- [ ] 5.1 Apply design D5. Verify: `grep -n "已探明" docs/development/map-panel-protocol.md docs/development/continental-geography.md` shows no sentence tying the announcement or the lighting to a first arrival.
- [ ] 5.2 Run `uv run --locked python -m tools.observability_lint check`, `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.contract_gate --change landmark-rite-lighting` and `openspec validate landmark-rite-lighting --strict`. Verify: all exit 0.

## Workflow follow-up

- During archive, after the delta sync, move the `covers_requirement` annotations of the two REMOVED requirements to the tests of the ADDED requirements, using the identifiers printed by `uv run --locked python -m tools.spec_traceability list`.
