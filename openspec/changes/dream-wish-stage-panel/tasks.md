# Tasks

Test prefix: `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`
(`/tmp/mud-test.env` contains the single line `MUD_TEST_SETTINGS=1`; create it if missing).
Run pnpm commands in `web/webclient-app`.

## 1. Panel

- [ ] 1.1 Port `components/DreamPanel.vue` per design decisions 1–6. Verify `grep -n "initialLayer\|state\.sample\|penned\|settleShown\|strokes\|reqs\b\|leaving\|departed\|direction_parts\|draft_preferences\|requirement_version\|state\.requirements" web/webclient-app/components/DreamPanel.vue` prints nothing and `pnpm run build` succeeds.
- [ ] 1.2 Rewrite `tests/dream.test.js` per design decision 9 with one case per scenario of `specs/webclient-dream-stage/spec.md`. Verify `pnpm exec vitest run tests/dream.test.js` passes.

## 2. Stories, bridge and copy

- [ ] 2.1 Create `stories/fixtures/dream_wish.js` and rewrite `stories/World/DreamPanel.stories.js` per design decision 8. Verify `pnpm run build-storybook` and `pnpm run showcase-coverage` pass.
- [ ] 2.2 Update `web/webclient/tests/test_vue_dream_stage_evidence.py` per design decision 10. Verify `<prefix> web.webclient.tests.test_vue_dream_stage_evidence` passes.
- [ ] 2.3 Apply design decision 7 (`OPENING`) and design decision 11 (documents). Verify `<prefix> world.narrative.tests.test_dream_surface` passes and `grep -n "念頭" docs/game/command-reference.md docs/game/commands.md web/webclient-app/components/DreamPanel.vue` prints nothing.

## 3. Gates

- [ ] 3.1 Run `pnpm test` and `pnpm run build`; both pass.
- [ ] 3.2 Run `uv run --locked python -m unittest tests.test_command_docs`, `uv run --locked python -m tools.spec_traceability check --change dream-wish-stage-panel` and `uv run --locked python -m tools.contract_gate --change dream-wish-stage-panel`; all pass.
- [ ] 3.3 Run `openspec validate dream-wish-stage-panel --strict`; it passes.

## Workflow follow-up

- Traceability at archive, after the delta is synced: add `covers_requirement` (IDs from `uv run --locked python -m tools.spec_traceability list`) to the bridge methods added in task 2.2 for "The keepsake card shows the current wish and stage-specific rows", "The whole wish is read-only while conversing", "Finalize asks before giving up remaining exchanges", "The thread choice sits above the reply bar before the first message" and "The edit sheet edits the wish only when finalized".
- Human review: a person compares the built panel with Storybook `Design/DreamWish` at that story's reference and Full HD viewports and reads the wording against the "Player-Facing Wording" table.
