# Tasks

Test prefix: `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`
(`/tmp/mud-test.env` contains the single line `MUD_TEST_SETTINGS=1`; create it if missing).

## 1. Working proposal on the surface

- [ ] 1.1 In `world/narrative/dream_surface.py` apply design decisions 1–3 (association keys, `offered_threads`, `wish_state`, `working_direction`, `choose_thread`, `lock_thread`, changed `store_response`, removed `store_direction`, `dream_state` reading the proposal). Verify `grep -n "store_direction\|\"direction\"" world/narrative/dream_surface.py` prints nothing.
- [ ] 1.2 In `server/dream_service.py::act` apply design decisions 4–6 (`say` wiring and stale condition, `choose_thread`, drafts from the working proposal). Add the tests of design decision 8 for both `dream-session-lifecycle` requirements in the delta spec and repair the existing tests. Verify `<prefix> world.narrative.tests.test_dream_surface` passes.

## 2. Web action

- [ ] 2.1 Apply design decision 7 (`dream.choose_thread` validator and registration, command echo entry, echo test case, coverage manifest id, registry enumeration). Verify `<prefix> web.webclient.actions.tests.test_dispatcher.test_registry` passes and `node --test web/static/webclient/js/tests/command_echo.test.js` passes.

## 3. Gates

- [ ] 3.1 Run `uv run --locked python -m tools.observability_lint check`, `uv run --locked python -m tools.test_data_lint check` and `uv run --locked python -m tools.contract_gate --change dream-working-proposal`; all pass.
- [ ] 3.2 Run `openspec validate dream-working-proposal --strict`; it passes.

## Workflow follow-up

- Traceability at archive, after the delta is synced: add `covers_requirement` (IDs from `uv run --locked python -m tools.spec_traceability list`) to the new tests in `world/narrative/tests/test_dream_surface.py`: the message, accumulation, report, failure, stale, draft and resume tests → "The session keeps a working proposal that only settled exchanges change"; the choice, default, lock, unoffered and resume-lock tests → "Thread choice precedes the first message and then locks".
