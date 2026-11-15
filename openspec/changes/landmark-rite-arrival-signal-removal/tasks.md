# Tasks

Run only the focused commands named below. `/tmp/mud-test.env` holds the single line `MUD_TEST_SETTINGS=1`; "the test prefix" means `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`; "the browser prefix" means `uv run --locked --env-file=/tmp/mud-test.env python -m web.tests.browser.unittest_driver`. Vitest: `pnpm test -- <file>`. Node gate: `node --test <file>`.
Do not add `covers_requirement` for ADDED requirements in this change; that happens at archive.

## 1. Preconditions

- [x] 1.1 Confirm `landmark-rite-lighting` is merged: `uv run --locked python -c "from world.rules.map_district_lighting import readable_lit_district_keys"` exits 0. If not, stop and report.

## 2. Server

- [x] 2.1 Apply design D1 to `travel_interrupts.py` and update `world/rules/tests/test_travel_interrupts.py` per design D3. Verify: the test prefix with `world.rules.tests.test_travel_interrupts` passes.
- [x] 2.2 Apply design D1 to `travel_events.py` and `travel_log.py` and update `world/rules/tests/test_travel_events.py`, `web/webclient/presentation/tests/test_travel_log.py` and `web/webclient/presentation/tests/test_world_map.py` per design D3. Verify: the test prefix passes for each of the three labels (three commands).

## 3. Browser

- [ ] 3.1 Apply design D2 to the protocol files and update `travel_log.test.js` and `protocol_immutable.test.js`. Verify: `node --test web/static/webclient/js/tests/travel_log.test.js` and `node --test web/static/webclient/js/tests/protocol_immutable.test.js` pass, and `uv run --locked python -m unittest tests.test_panel_schema_version_parity_contract` passes.
- [ ] 3.2 Apply design D2 to the store, `leg-model.js`, `LandmarkCard.vue`, the fixtures and the stories, and update `landmark.test.js` and `route-walking.test.js`. Verify: `pnpm test -- web/webclient-app/tests/travel` passes.
- [ ] 3.3 Update `web/tests/browser/test_wilderness_travel.py` and `web/tests/browser/travel_log_fixture.py`. Verify: after `pnpm run build`, the browser prefix with `web.tests.browser.test_wilderness_travel.TravelRouteTests` passes and the browser prefix with `web.tests.browser.test_wilderness_travel.TravelLogTests` passes (two commands).

## 4. Documentation and gates

- [ ] 4.1 Apply design D4. Verify: `grep -rnE "district_lit|\blit_district\b|\blitDistrict\b" --include=*.py --include=*.js --include=*.vue --include=*.md --include=*.json . --exclude-dir=node_modules --exclude-dir=dist --exclude-dir=.worktrees --exclude-dir=archive --exclude-dir=superpowers --exclude-dir=design --exclude-dir=.storybook-out` prints only lines under `openspec/changes/landmark-rite-`.
- [ ] 4.2 Run `pnpm run build-storybook` then `pnpm run showcase-coverage`, `uv run --locked python -m unittest tests.test_webclient_frozen_contract`, `uv run --locked python -m tools.contract_gate --change landmark-rite-arrival-signal-removal` and `openspec validate landmark-rite-arrival-signal-removal --strict`. Verify: all exit 0.

## Workflow follow-up

- During archive, after the delta sync, annotate the tests of the two ADDED requirements with the identifiers printed by `uv run --locked python -m tools.spec_traceability list`.
