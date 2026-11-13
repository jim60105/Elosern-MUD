# Tasks

Test prefix: `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`
(`/tmp/mud-test.env` contains the single line `MUD_TEST_SETTINGS=1`; create it if missing).
Run `pnpm run build` and the Storybook commands in `web/webclient-app`; run `pnpm exec vitest run <file>` from the repository root, where the Vitest config lives. Run only the focused test labels named below — one module, one Node file or one Vitest file at a time. Never run a whole test suite for this change.

## 1. Server line

- [x] 1.1 Apply design decision 1 in `world/narrative/dream_surface.py` and add the `dream-sleep-surface` and `dream-explicit-presentation` scenario tests of design decision 5 to `world/narrative/tests/test_dream_surface.py` (the phase is asserted through `ending_phase`, never through ending text). Verify `<prefix> world.narrative.tests.test_dream_surface` passes and `git diff --stat -- server/dream_service.py commands/dream.py` prints nothing.

## 2. Browser farewell

- [x] 2.1 Create `composables/use-dream-farewell.js` per design decision 2 and `tests/dream_farewell.test.js` per design decision 5. Verify `pnpm exec vitest run tests/dream_farewell.test.js` passes.
- [x] 2.2 Apply design decision 3 (`use-app-client.js`, `AppClient.vue`, `use-sleep-handoff.js`, the store flag and the travel model and its two store call sites) and add the sleep-handoff-option, store-flag and travel-layout cases of design decision 5. Verify `pnpm exec vitest run tests/app_client_sleep_handoff.test.js tests/travel/layout.test.js` passes.
- [x] 2.3 Apply design decision 4 in `components/DreamPanel.vue` and add the panel cases of design decision 5 to `tests/dream.test.js`. Verify `pnpm exec vitest run tests/dream.test.js` passes.

## 3. Stories and bridge

- [x] 3.1 Apply design decision 6 (stories) and the bridge method of design decision 5. Verify `pnpm run build-storybook`, `pnpm run showcase-coverage` and `<prefix> web.webclient.tests.test_vue_dream_stage_evidence` pass.

## 4. Gates

- [ ] 4.1 Run `pnpm exec vitest run tests/dream_farewell.test.js tests/dream.test.js tests/app_client_sleep_handoff.test.js tests/travel/layout.test.js` (from the repository root) and `pnpm run build`; all pass. Do not run the whole `pnpm test` suite.
- [ ] 4.2 Run `uv run --locked python -m tools.test_data_lint check` and `uv run --locked python -m tools.contract_gate --change dream-farewell-beat`; both pass.
- [ ] 4.3 Run `openspec validate dream-farewell-beat --strict`; it passes.

## Workflow follow-up

- Traceability at archive, after the delta is synced: add `covers_requirement` (IDs from `uv run --locked python -m tools.spec_traceability list`) to the server tests of task 1.1 for "Departure ends with a server-authored farewell line" and to the bridge method of task 3.1 for "A live departure plays a farewell before the stage releases".
- Human review: a person reads the six lines of `FAREWELL_LINES` and watches the transition against the source design's "Farewell" section and Storybook `Design/DreamWish`.
