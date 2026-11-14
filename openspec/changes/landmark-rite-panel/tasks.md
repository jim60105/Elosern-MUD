# Tasks

Run only the focused commands named below. `/tmp/mud-test.env` holds the single line `MUD_TEST_SETTINGS=1`; "the test prefix" means `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`.
Do not add `covers_requirement` for ADDED requirements in this change; that happens at archive.
Tests use the synthetic landmark fixture and synthetic text only.

## 1. Preconditions

- [x] 1.1 Confirm `landmark-rite-action` is merged: `uv run --locked python -c "from web.webclient.actions.rite_actions import landmark_rite_adapter, rite_delivery"` exits 0. If not, stop and report.

## 2. Server panel

- [x] 2.1 Create `web/webclient/presentation/rite.py` with the constants and `validate_rite` per design D1 and D2, and the pure validator tests of design D6 in `web/webclient/presentation/tests/test_rite_panel.py`; register the test module in `.github/evennia-shards.json`. Verify: the test prefix with `web.webclient.presentation.tests.test_rite_panel` passes.
- [x] 2.2 Add `rite_presenter` and `store_rite_delivery` per design D2, the registration and validator attachment, the adapter call of design D3, and the presenter tests of design D6. Add `rite` to the exact panel set of `web/webclient/presentation/tests/test_combat_panel/test_presenter.py`. Verify: the same test label passes, and the test prefix passes for `web.webclient.actions.tests.test_rite_actions` and for `web.webclient.presentation.tests.test_combat_panel.test_presenter` (two commands).

## 3. Browser mirror

- [x] 3.1 Apply design D4 to `constants.js`, `panels/rite.js`, `envelope.js`, `protocol.js`, `shared.js` and the parity contract tuple. Create `web/static/webclient/js/tests/rite_panel.test.js` per design D6. Verify: `node --test web/static/webclient/js/tests/rite_panel.test.js` passes, `node --test web/static/webclient/js/tests/travel_log.test.js` passes, and `uv run --locked python -m unittest tests.test_panel_schema_version_parity_contract` passes.
- [x] 3.2 Run `pnpm test -- web/webclient-app/tests/travel/log.test.js`. Verify: it passes (the panel name list change breaks no existing store test). If another Vitest file enumerates every panel name and fails, add `rite` to its expectation and name the file in the hand-off.

## 4. Documentation and gates

- [x] 4.1 Add the `rite` panel section per design D5. Verify: `grep -c "rite" docs/development/webclient-synchronization.md` prints a larger number than before the edit.
- [x] 4.2 Run `uv run --locked python -m unittest tests.test_webclient_frozen_contract`, `uv run --locked python -m tools.observability_lint check`, `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.contract_gate --change landmark-rite-panel` and `openspec validate landmark-rite-panel --strict`. Verify: all exit 0. If the frozen contract fails because it enumerates panels, update its enumeration in this change and name the edit in the hand-off.

## Workflow follow-up

- During archive, after the delta sync, annotate the tests of the four ADDED requirements with the identifiers printed by `uv run --locked python -m tools.spec_traceability list`.
