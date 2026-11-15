# Tasks

Run only the focused commands named below, from the repository root. "The test prefix" means `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`; "the browser prefix" means `uv run --locked --env-file=/tmp/mud-test.env python -m web.tests.browser.unittest_driver`; `/tmp/mud-test.env` holds the single line `MUD_TEST_SETTINGS=1`. Run `pnpm run build` before any browser command. Vitest: `pnpm test -- <file>`.
Do not add `covers_requirement` for the ADDED requirement in this change; that happens at archive.

## 1. Preconditions

- [x] 1.1 Confirm `landmark-rite-stage` is merged: `ls web/webclient-app/composables/use-rite-stage.js web/webclient-app/tests/app_client_rite.test.js` lists two files. If not, stop and report.

## 2. Journeys

- [x] 2.1 Create `web/tests/browser/test_landmark_rite.py` with `test_wilderness_rite_journey` per design D1 and register it in `.github/browser-shards.json`. Fix exposed defects per design D2. Verify: after `pnpm run build`, the browser prefix with `web.tests.browser.test_landmark_rite.LandmarkRiteTests.test_wilderness_rite_journey` passes.
- [x] 2.2 Add `test_city_rite_journey` per design D1 and register it. Verify: after `pnpm run build`, the browser prefix with `web.tests.browser.test_landmark_rite.LandmarkRiteTests.test_city_rite_journey` passes.
- [x] 2.3 Run the browser prefix with `web.tests.browser.test_wilderness_travel.TravelRouteTests`. Verify: it passes (the generic landmark card still opens when no rite panel is available).

## 3. Gates

- [x] 3.1 If a component or binding was changed, run `pnpm test -- web/webclient-app/tests/rite` and `pnpm test -- web/webclient-app/tests/app_client_rite.test.js`. Verify: both pass.
- [x] 3.2 Run the test prefix with `tests.test_evennia_test_optimization_contract`; `uv run --locked python -m unittest tests.test_webclient_frozen_contract`; `uv run --locked python -m tools.contract_gate --change landmark-rite-journeys`; `openspec validate landmark-rite-journeys --strict`. Verify: all exit 0.

## Workflow follow-up

- During archive, after the delta sync, annotate the two journey tests with the identifier printed by `uv run --locked python -m tools.spec_traceability list`.
