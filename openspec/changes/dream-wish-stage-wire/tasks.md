# Tasks

Test prefix: `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`
(`/tmp/mud-test.env` contains the single line `MUD_TEST_SETTINGS=1`; create it if missing).
Run `pnpm run build` and the Storybook commands in `web/webclient-app`; run `pnpm exec vitest run <file>` from the repository root, where the Vitest config lives. Run only the focused test labels named below — one module, one Node file or one Vitest file at a time. Never run a whole test suite for this change.

## 1. Read model and wire

- [x] 1.1 Apply design decision 1 in `world/narrative/dream_surface.py::dream_state` and add the read-model assertions of design decision 5 to `world/narrative/tests/test_dream_surface.py`. Verify `<prefix> world.narrative.tests.test_dream_surface` passes.
  — Also moves the text line's requirement rows off `can_confirm` and onto the open session: with confirmation scoped to the finalized stage, gating on it would hide the rows while conversing and break the unchanged `dream-authoring` requirement that both surfaces name them before anything is frozen.
- [x] 1.2 Apply design decision 2 (schema 4 on both sides, the literal on `protocol/panels/dream.js` line 15, the eight keys and their rules) and the fixture-only edits of design decision 5. Verify `node --test web/static/webclient/js/tests/protocol_dream.test.js` passes, `pnpm exec vitest run tests/dream.test.js` passes, and `<prefix> web.webclient.presentation.tests.test_dream_artwork tests.test_panel_schema_version_parity_contract` passes.
- [x] 1.3 Apply design decision 3: the envelope test in `web/webclient/presentation/tests/test_dream_artwork.py`. Verify it passes and that raising either aggregate budget makes it fail before you revert.
  — The largest legal state is 239 bytes over the 65,536-byte envelope at the shipped 16,384/8,192 pair, so design decision 3's own remedy applies: `MAX_CHANGES_BYTES` becomes 7,680, reserving one bounded list item. Raising `MAX_PROPOSAL_BYTES` to 20,480 published 69,369 bytes and raising `MAX_CHANGES_BYTES` back to 8,192 published 65,775 bytes; both failed the assertion and were reverted.

## 2. Web action

- [x] 2.1 Apply design decision 4 (`dream.finalize` validator, registration, echo, echo test, manifest id, registry enumeration). Both roster scenarios of `specs/webclient-action-dispatch/spec.md` must hold, since they now list `dream.finalize` and count six dream adapters. Verify `<prefix> web.webclient.actions.tests.test_dispatcher.test_registry` passes and `node --test web/static/webclient/js/tests/command_echo.test.js` passes.
  — The shared exact-key validator already yields exactly `session_id` and `revision` for `finalize`; `world.narrative.tests.test_dream_surface.test_finalize_payload_validation` pins it. The manifest id also lands in the per-surface behavioral table and the registry catalog pin, which both enumerate the manifest.

## 3. Gates

- [x] 3.1 Run `pnpm run build`, `uv run --locked python -m tools.test_data_lint check` and `uv run --locked python -m tools.contract_gate --change dream-wish-stage-wire`; all pass.
- [x] 3.2 Run `openspec validate dream-wish-stage-wire --strict`; it passes.

## Workflow follow-up

- Traceability at archive, after the delta is synced: the new `webclient-dream-stage` scenario "Stage fields are validated together" is established by the `protocol_dream.test.js` schema-4 cases; add `covers_requirement` where the existing evidence bridge names them. The `webclient-action-dispatch` delta is established by `test_registry.py`, which already carries its requirement annotation.
