# Tasks

Test prefix: `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py`
(`/tmp/mud-test.env` contains the single line `MUD_TEST_SETTINGS=1`; create it if missing).
This change adds a migration: run the first Evennia test command of this change with `--noinput` and without `--keepdb`; later commands may add `--keepdb`.
Run pnpm commands in `web/webclient-app`.

## 1. Stage in the lifecycle

- [ ] 1.1 Add `DreamSession.stage` and `world/narrative/migrations/0013_dream_session_stage.py` (design decision 1). Verify `uv run --locked --env-file=/tmp/mud-test.env evennia makemigrations narrative --check --dry-run --settings test_settings.py` reports no pending change.
- [ ] 1.2 Apply design decision 2 in `world/narrative/dream_session.py` and add the `test_dream_session.py` tests of design decision 10. Verify `<prefix> --noinput world.narrative.tests.test_dream_session` passes.

## 2. Service and surface

- [ ] 2.1 Apply design decisions 3–7 in `world/narrative/dream_surface.py` and `server/dream_service.py`. Add and repair the `test_dream_surface.py` tests of design decision 10. Verify `<prefix> --keepdb world.narrative.tests.test_dream_surface` passes.

## 3. Wire and web action

- [ ] 3.1 Apply design decision 8 (schema 4 on both sides, validator rules) and the fixture-only edits of design decision 10. Verify `node --test web/static/webclient/js/tests/protocol_dream.test.js` passes, `pnpm exec vitest run tests/dream.test.js` passes, and `<prefix> --keepdb web.webclient.presentation.tests.test_dream_artwork tests.test_panel_schema_version_parity_contract` passes.
- [ ] 3.2 Apply design decision 9 (`dream.finalize` validator, registration, echo, echo test, manifest id, registry enumeration). Verify `<prefix> --keepdb web.webclient.actions.tests.test_dispatcher.test_registry` passes and `node --test web/static/webclient/js/tests/command_echo.test.js` passes.

## 4. Gates

- [ ] 4.1 Run `pnpm run build`, `pnpm run build-storybook` and `pnpm run showcase-coverage`; all pass.
- [ ] 4.2 Run `uv run --locked python -m tools.observability_lint check`, `uv run --locked python -m tools.test_data_lint check`, `<prefix> --keepdb web.webclient.tests.test_vue_dream_stage_evidence` and `uv run --locked python -m tools.contract_gate --change dream-wish-stages`; all pass.
- [ ] 4.3 Run `openspec validate dream-wish-stages --strict`; it passes.

## Workflow follow-up

- Traceability at archive, after the delta is synced: add `covers_requirement` for the new requirement "A session is conversing until it is finalized" (ID from `uv run --locked python -m tools.spec_traceability list`) to the stage tests in `world/narrative/tests/test_dream_session.py` and `world/narrative/tests/test_dream_surface.py`.
