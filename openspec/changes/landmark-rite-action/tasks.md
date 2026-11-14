# Tasks

Run only the focused commands named below. `/tmp/mud-test.env` holds the single line `MUD_TEST_SETTINGS=1`; "the test prefix" means `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`.
Do not add `covers_requirement` for ADDED requirements in this change; that happens at archive.
Tests use the synthetic landmark fixture and synthetic text only.

## 1. Preconditions

- [ ] 1.1 Confirm `landmark-rite-settlement` and `landmark-rite-content-completion` are merged (`grep -c provisional world/lore/rites/content/landmark_rites.yaml` prints 0): `uv run --locked python -c "from world.rules.landmark_rites import perform_rite, RiteRefused, REFUSAL_MESSAGES; from world.lore.rites import load_published"` exits 0. If not, stop and report.

## 2. Action

- [ ] 2.1 Create `web/webclient/actions/rite_actions.py` with the helpers of design D1 and the validator and adapter of design D2. Register the action and add it to `_REQUEST_IDENTITY_ACTIONS` and to the identifiers listed in `web/webclient/actions/tests/test_dispatcher/test_registry.py`. Create `web/webclient/actions/tests/test_rite_actions.py` per design D5 and register it in `.github/evennia-shards.json`. Apply the command echo paragraph of design D2 to the manifest, `command_echo.js` and `command_echo.test.js`. Verify: the test prefix passes for each of `web.webclient.actions.tests.test_rite_actions`, `web.webclient.actions.tests.test_dispatcher.test_registry` and `web.webclient.actions.tests.test_action_catalog_coverage` (three commands), and `node --test web/static/webclient/js/tests/command_echo.test.js` passes.
- [ ] 2.2 Add the `explore.landmark_rite` bullet to `docs/development/webclient-synchronization.md` per design D4. Verify: `grep -c explore.landmark_rite docs/development/webclient-synchronization.md` prints at least 1.

## 3. Text command

- [ ] 3.1 Create `commands/rite.py` per design D3 and mount it in `commands/default_cmdsets.py`. Create `commands/tests/test_rite_command.py` per design D5 and register it in `.github/evennia-shards.json`. Verify: the test prefix with `commands.tests.test_rite_command` passes.
- [ ] 3.2 Document the command in `docs/game/commands.md` and `docs/game/command-reference.md` per design D4. Verify: `uv run --locked python -m unittest tests.test_command_docs` passes.

## 4. Gates

- [ ] 4.1 Run `uv run --locked python -m tools.observability_lint check`, `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.contract_gate --change landmark-rite-action` and `openspec validate landmark-rite-action --strict`. Verify: all exit 0.

## Workflow follow-up

- During archive, after the delta sync, annotate the tests of the four ADDED requirements with the identifiers printed by `uv run --locked python -m tools.spec_traceability list`.
