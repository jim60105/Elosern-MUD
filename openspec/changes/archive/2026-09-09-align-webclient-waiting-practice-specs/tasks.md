# Tasks: Align waiting and practice specifications with the shipped WebClient

All behavior is already shipped and green on this branch; verification here is
specification-mechanical plus traceability annotation, not re-implementation.

## 1. Delta fidelity

- [x] 1.1 Diff every MODIFIED block in `specs/webclient-exploration-menu/spec.md` and `specs/webclient-contextual-hud/spec.md` against the current main-spec text; the only differences are the amended clauses (wait sentence, `skill` field, footer carve-out) — no accidental scenario loss or wording drift.
- [x] 1.2 Confirm the action-dispatch ID list is set-equal to `build_production_registry()`'s registered IDs (the same comparison `test_dispatcher.py::test_production_registry_exposes_only_specified_adapters` pins) and to the dispatcher test's enumeration literal.

## 2. Validation

- [x] 2.1 `uv run --locked python -m tools.spec_traceability check` stays green (no dangling annotations introduced by the delta alone).
- [x] 2.2 `openspec validate align-webclient-waiting-practice-specs --strict` passes.

## 3. Traceability (after the delta is merged/synced so the new IDs exist in `openspec/specs/`)

- [x] 3.1 Annotate the existing substantive evidence with `@covers_requirement` using literal IDs from `uv run --locked python -m tools.spec_traceability list`:
  - `webclient-exploration-menu::explorepracticeadvancestheclockforonedeclaredskill` → the four declared-growth/unknown-capped/ambiguous-payload/rollback tests in `web/webclient/actions/tests/test_exploration_actions.py` (one ID per owning test, per the established pattern).
  - `webclient-exploration-menu::thewaitingsurfaceoffersexactlythreeoperations` → the Python evidence-runner pattern over the vitest waiting-form tests (`tests/test_node_suite_evidence.py` precedent), or the equivalent focused vitest evidence test.
  - `webclient-contextual-hud::theskillbookoffersaboundeddeclaredpracticesubscreen` → the practice-screen vitest evidence through the same runner pattern.
  - The amended action-dispatch enumeration and tampered-field requirements keep their existing annotations (`test_production_registry_exposes_only_specified_adapters`, tampered-input tests); confirm `check` still maps them after the edit.
- [x] 3.2 Re-run `uv run --locked python -m tools.spec_traceability check` after sync+annotation: green.

## 4. Focused regression (confirmation only)

- [x] 4.1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.actions.tests.test_exploration_actions web.webclient.actions.tests.test_dispatcher` green.
- [x] 4.2 `pnpm exec vitest run tests/action/` (waiting cards, RestForm hours bounds, practice screen) green.

## 5. Spec hygiene (found during the audit, fixed in this change's sync)

- [x] 5.1 Fix the stale purpose census in `webclient-exploration-menu/spec.md` Purpose: the exploration adapter family now counts thirteen, not eight.
- [x] 5.2 Fix the stale adapter census in `web/webclient/actions/registry.py` module docstring if it still says twelve exploration adapters (comment-only edit).
