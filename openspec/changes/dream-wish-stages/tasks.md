# Tasks

Test prefix: `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py`
(`/tmp/mud-test.env` contains the single line `MUD_TEST_SETTINGS=1`; create it if missing).
This change adds a migration: run the first Evennia test command of this change with `--noinput` and without `--keepdb`; later commands may add `--keepdb`.
Run only the focused test labels named below — one module at a time. Never run a whole test suite for this change.

## 1. Stage in the lifecycle

- [x] 1.1 Add `DreamSession.stage` and `world/narrative/migrations/0013_dream_session_stage.py` per design decision 1: one `AddField` and no data migration. Verify `uv run --locked --env-file=/tmp/mud-test.env evennia makemigrations narrative --check --dry-run --settings test_settings.py` reports no pending change and that the migration file contains no `RunPython`.
- [x] 1.2 Apply design decision 2 in `world/narrative/dream_session.py` and add the `test_dream_session.py` tests of design decision 7. Verify `<prefix> --noinput world.narrative.tests.test_dream_session` passes.

## 2. Service and surface

- [x] 2.1 Apply design decisions 3–6 in `world/narrative/dream_surface.py` and `server/dream_service.py` (stage gates including `choose_thread`, `store_proposal`, the `thread_id` presence rule, the draft/confirm/awaken rewrite). Add and repair the `test_dream_surface.py` tests of design decision 7. Verify `<prefix> --keepdb world.narrative.tests.test_dream_surface` passes.

## 3. Gates

- [x] 3.1 Run `uv run --locked python -m tools.observability_lint check`, `uv run --locked python -m tools.test_data_lint check` and `uv run --locked python -m tools.contract_gate --change dream-wish-stages`; all pass.
- [x] 3.2 Run `openspec validate dream-wish-stages --strict`; it passes.

## Workflow follow-up

- Traceability at archive, after the delta is synced: add `covers_requirement` for "A session is conversing until it is finalized" to the stage, finalize, thread-choice and thread-form tests, and for "A later sleep reopens an unfinalized conversation" to the resume and at-cap tests, in `world/narrative/tests/test_dream_session.py` and `world/narrative/tests/test_dream_surface.py` (IDs from `uv run --locked python -m tools.spec_traceability list`).
