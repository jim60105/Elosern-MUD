# Tasks

Test prefix: `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`
(`/tmp/mud-test.env` contains the single line `MUD_TEST_SETTINGS=1`; create it if missing).

## 1. Command

- [ ] 1.1 In `commands/dream.py` apply design decisions 1–3 (`_USAGE`, routing of `thread` and `finalize`, `render_changes`, `render_wish`, `render_threads`, `render_state(state, *, changes_last=False)`, class docstring usage line). Add the tests of design decision 5 and update the existing text assertions. Verify `<prefix> world.narrative.tests.test_dream_surface` passes.

## 2. Documents

- [ ] 2.1 Apply design decisions 1 and 4 to `tests/test_command_docs.py` (manifest syntax), `docs/game/command-reference.md` and `docs/game/commands.md`. Verify `uv run --locked python -m unittest tests.test_command_docs` passes and `grep -n "requirement_version\|已檢視的版本\|尚未檢視" docs/game/command-reference.md docs/game/commands.md` prints nothing.

## 3. Gates

- [ ] 3.1 Run `uv run --locked python -m tools.observability_lint check`, `uv run --locked python -m tools.test_data_lint check` and `uv run --locked python -m tools.contract_gate --change dream-wish-text-commands`; all pass.
- [ ] 3.2 Run `openspec validate dream-wish-text-commands --strict`; it passes.

## Workflow follow-up

- Traceability at archive, after the delta is synced: add `covers_requirement` for the new requirement "Text dream commands reach thread choice, finalize and the change report" (ID from `uv run --locked python -m tools.spec_traceability list`) to the new text tests in `world/narrative/tests/test_dream_surface.py`.
- Human review: a person reads the command output wording and the two documentation pages against the source design's "Player-Facing Wording" table.
