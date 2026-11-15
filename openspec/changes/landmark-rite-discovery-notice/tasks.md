# Tasks

Run only the focused commands named below. `/tmp/mud-test.env` holds the single line `MUD_TEST_SETTINGS=1`; "the test prefix" means `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`. Vitest: `pnpm test -- <file>`.
Do not add `covers_requirement` for ADDED requirements in this change; that happens at archive.

## 1. Preconditions

- [x] 1.1 Confirm `landmark-rite-lighting` is merged: `uv run --locked python -c "from world.rules.map_district_lighting import readable_lit_district_keys"` exits 0, and `grep -c "已探明" world/rules/map_discovery.py` prints 0. If not, stop and report.

## 2. Server

- [x] 2.1 Apply design D1 with the server tests of design D4. Verify: the test prefix passes for each of `web.webclient.actions.tests.test_rite_actions`, `commands.tests.test_rite_command`, `world.rules.tests.test_landmark_rites` (three commands).
- [x] 2.2 Apply design D3. Verify: `uv run --locked python -m unittest tests.test_command_docs` passes.

## 3. Browser

- [x] 3.1 Apply design D2 with the Vitest tests of design D4. Verify: `pnpm test -- web/webclient-app/tests/rite/store.test.js` and `pnpm test -- web/webclient-app/tests/app_client_rite.test.js` pass.

## 4. Gates

- [x] 4.1 Run `uv run --locked python -m tools.observability_lint check`, `uv run --locked python -m tools.contract_gate --change landmark-rite-discovery-notice` and `openspec validate landmark-rite-discovery-notice --strict`. Verify: all exit 0.

## Workflow follow-up

- During archive, after the delta sync, annotate the tests of the two ADDED requirements with the identifiers printed by `uv run --locked python -m tools.spec_traceability list`.
