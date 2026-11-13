# Tasks

Test prefix: `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`
(`/tmp/mud-test.env` contains the single line `MUD_TEST_SETTINGS=1`; create it if missing).
Run only the focused test labels named below — one module, one Node file or one Vitest file at a time. Never run a whole test suite for this change.

## 1. Model contract

- [x] 1.1 In `world/ai/dream.py` apply design decisions 1–7 (import, schema, `DreamExchange`, `_make_edits_validator`, `_edit_text`, `build_dream_prompt`, `generate_dream_exchange`). Update and extend `world/ai/tests/test_dream_presentation.py` per design decision 10 so every scenario of `specs/dream-explicit-presentation/spec.md` has a test. Verify `<prefix> world.ai.tests.test_dream_presentation world.ai.tests.test_dream_frame_contract` passes.
- [x] 1.2 Edit `prompts/dream.yaml` per design decision 8. Verify `<prefix> world.prompts.tests.test_loader` passes and `uv run --locked python -c "from world.prompts.loader import render_prompt; print(render_prompt('dream.system', phase='p', climax_phase='c', mode='exchange', exchange_number='1', remaining='5'))"` prints the rendered prompt containing `edits` and `str_replace` with no unresolved `{` placeholder error.

## 2. Surface bridge and fixtures

- [x] 2.1 Apply design decision 9 in `world/narrative/dream_surface.py::store_response` and update the fixtures and the drift test named in design decision 10 (`test_dream_surface.py`, `test_dream_dispatch.py`, `web/tests/browser/seed/dream_fixture.py` if it records `requirements`). Verify `<prefix> world.narrative.tests.test_dream_surface world.narrative.tests.test_dream_dispatch` passes.

## 3. Gates

- [x] 3.1 Run `uv run --locked python -m tools.observability_lint check`, `uv run --locked python -m tools.test_data_lint check` and `uv run --locked python -m tools.contract_gate --change dream-collaborator-proposal-edits`; all pass.
- [x] 3.2 Run `openspec validate dream-collaborator-proposal-edits --strict`; it passes.

## Workflow follow-up

- Traceability at archive, after the delta is synced: add `covers_requirement` for the new requirement "Collaborator responses carry proposal edits validated by application" (ID from `uv run --locked python -m tools.spec_traceability list`) to the valid-edits, retry, exhausted-retry and forbidden-content tests in `world/ai/tests/test_dream_presentation.py`.
- Human review: a person reads the changed `prompts/dream.yaml` against the source design's "Edit Contract" section.
