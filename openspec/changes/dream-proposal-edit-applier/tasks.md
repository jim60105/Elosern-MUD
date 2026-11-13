# Tasks

Test prefix: `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`
(`/tmp/mud-test.env` contains the single line `MUD_TEST_SETTINGS=1`; create it if missing).

## 1. Applier module

- [ ] 1.1 Create `world/narrative/dream_proposal.py` exactly as design decisions 1–8 state (constants, `ProposalEditError`, `ERROR_CODES`, the seven public functions). Verify `uv run --locked python -c "import sys, world.narrative.dream_proposal as m; assert 'django' not in sys.modules; print(m.PATHS, m.apply_edits(m.empty_proposal(), []))"` prints the seven paths and an empty proposal.
- [ ] 1.2 Create `world/narrative/tests/test_dream_proposal.py` per design decision 9 with one test method per scenario of `specs/dream-proposal-editing/spec.md`, and register `world.narrative.tests.test_dream_proposal` in `.github/evennia-shards.json` beside `world.narrative.tests.test_dream_session`. Verify `<prefix> world.narrative.tests.test_dream_proposal` passes and `<prefix> tests.test_evennia_test_optimization_contract` passes.

## 2. Gates

- [ ] 2.1 Run `uv run --locked python -m tools.contract_gate --change dream-proposal-edit-applier`; it passes.
- [ ] 2.2 Run `openspec validate dream-proposal-edit-applier --strict`; it passes.

## Workflow follow-up

- Traceability at archive, after the delta is synced: add `covers_requirement` to the tests in `world/narrative/tests/test_dream_proposal.py` for the three new `dream-proposal-editing` requirements (IDs from `uv run --locked python -m tools.spec_traceability list`): the command and atomicity tests → "Edit commands apply in order and all or nothing"; the normalization, requirement-row, bounds and drift tests → "Edited fields are normalized and bounded"; the diff tests → "The change report names what an edit set changed".
