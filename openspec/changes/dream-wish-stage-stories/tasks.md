# Tasks

Test prefix: `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`
(`/tmp/mud-test.env` contains the single line `MUD_TEST_SETTINGS=1`; create it if missing).
Run `pnpm run build` and the Storybook commands in `web/webclient-app`. Run only the focused test labels named below — one module at a time. Never run a whole test suite for this change.

## 1. Stories

- [ ] 1.1 Create `stories/fixtures/dream_wish.js` and rewrite `stories/World/DreamPanel.stories.js` per design decisions 1 and 2. Verify `pnpm run build-storybook` and `pnpm run showcase-coverage` pass, and that every previous export name still exists.

## 2. Copy and documents

- [ ] 2.1 Apply design decision 3 (`OPENING`). Verify `<prefix> world.narrative.tests.test_dream_surface` passes.
- [ ] 2.2 Apply design decision 4 (the two documents). Verify `uv run --locked python -m unittest tests.test_command_docs` passes and `grep -n "念頭\|記下念頭" docs/game/command-reference.md docs/game/commands.md` prints nothing.

## 3. Gates

- [ ] 3.1 Run `pnpm run build`, `uv run --locked python -m tools.test_data_lint check` and `uv run --locked python -m tools.contract_gate --change dream-wish-stage-stories`; all pass.
- [ ] 3.2 Run `openspec validate dream-wish-stage-stories --strict`; it passes.
- [ ] Human review: a person compares the stories with Storybook `Design/DreamWish` and reads the two documents against the "Player-Facing Wording" table.
