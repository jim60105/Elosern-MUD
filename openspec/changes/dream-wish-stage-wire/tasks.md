# Tasks

Test prefix: `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`
(`/tmp/mud-test.env` contains the single line `MUD_TEST_SETTINGS=1`; create it if missing).
Run pnpm commands in `web/webclient-app`.

## 1. Read model and wire

- [ ] 1.1 Apply design decision 1 in `world/narrative/dream_surface.py::dream_state` and add the read-model assertions of design decision 5 to `world/narrative/tests/test_dream_surface.py`. Verify `<prefix> world.narrative.tests.test_dream_surface` passes.
- [ ] 1.2 Apply design decision 2 (schema 4 on both sides, the literal on `protocol/panels/dream.js` line 15, the eight keys and their rules) and the fixture-only edits of design decision 5. Verify `node --test web/static/webclient/js/tests/protocol_dream.test.js` passes, `pnpm exec vitest run tests/dream.test.js` passes, and `<prefix> web.webclient.presentation.tests.test_dream_artwork tests.test_panel_schema_version_parity_contract` passes.
- [ ] 1.3 Apply design decision 3: the envelope test in `web/webclient/presentation/tests/test_dream_artwork.py`. Verify it passes and that raising either aggregate budget makes it fail before you revert.

## 2. Web action

- [ ] 2.1 Apply design decision 4 (`dream.finalize` validator, registration, echo, echo test, manifest id, registry enumeration). Both roster scenarios of `specs/webclient-action-dispatch/spec.md` must hold, since they now list `dream.finalize` and count six dream adapters. Verify `<prefix> web.webclient.actions.tests.test_dispatcher.test_registry` passes and `node --test web/static/webclient/js/tests/command_echo.test.js` passes.

## 3. Gates

- [ ] 3.1 Run `pnpm run build`, `uv run --locked python -m tools.test_data_lint check` and `uv run --locked python -m tools.contract_gate --change dream-wish-stage-wire`; all pass.
- [ ] 3.2 Run `openspec validate dream-wish-stage-wire --strict`; it passes.

## Workflow follow-up

- Traceability at archive, after the delta is synced: the new `webclient-dream-stage` scenario "Stage fields are validated together" is established by the `protocol_dream.test.js` schema-4 cases; add `covers_requirement` where the existing evidence bridge names them. The `webclient-action-dispatch` delta is established by `test_registry.py`, which already carries its requirement annotation.
