# Tasks

Test prefix: `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`
(`/tmp/mud-test.env` contains the single line `MUD_TEST_SETTINGS=1`; create it if missing).
Run pnpm commands in `web/webclient-app`.

## 1. Change report

- [ ] 1.1 Apply design decisions 1 and 2 in `components/DreamPanel.vue`. Add the Vitest cases for "The keepsake card reports what the last exchange changed" and "The whole-wish view marks changes and names removed items" to `tests/dream.test.js`. Verify `pnpm exec vitest run tests/dream.test.js` passes.

## 2. Requirement rows

- [ ] 2.1 Apply design decision 3 in `components/DreamPanel.vue`. Add the Vitest cases for "Requirement rows are editable when finalized". Verify `pnpm exec vitest run tests/dream.test.js` passes.

## 3. Schema 5

- [ ] 3.1 Apply design decision 4 on the server, the validator, the constants and every fixture and test it names. Verify `grep -rn "direction_parts\|draft_preferences\|requirement_version" world/narrative/dream_surface.py web/webclient/presentation/dream.py web/static/webclient/js/elosern/protocol/panels/dream.js web/webclient-app/components commands/dream.py` prints nothing, `node --test web/static/webclient/js/tests/protocol_dream.test.js` passes, and `<prefix> world.narrative.tests.test_dream_surface web.webclient.presentation.tests.test_dream_artwork tests.test_panel_schema_version_parity_contract` passes.

## 4. Stories and bridge

- [ ] 4.1 Apply design decisions 5 and 6 (stories, bridge methods). Verify `pnpm run build-storybook`, `pnpm run showcase-coverage` and `<prefix> web.webclient.tests.test_vue_dream_stage_evidence` pass.

## 5. Gates

- [ ] 5.1 Run `pnpm test` and `pnpm run build`; both pass.
- [ ] 5.2 Run `uv run --locked python -m tools.test_data_lint check` and `uv run --locked python -m tools.contract_gate --change dream-wish-change-report`; both pass.
- [ ] 5.3 Run `openspec validate dream-wish-change-report --strict`; it passes.

## Workflow follow-up

- Traceability at archive, after the delta is synced: add `covers_requirement` (IDs from `uv run --locked python -m tools.spec_traceability list`) to the three bridge methods added in task 4.1 for "The keepsake card reports what the last exchange changed", "The whole-wish view marks changes and names removed items" and "Requirement rows are editable when finalized".
- Human review: a person compares the change line, the marks and the requirement rows with Storybook `Design/DreamWish` and reads the wording against the "Player-Facing Wording" table.
