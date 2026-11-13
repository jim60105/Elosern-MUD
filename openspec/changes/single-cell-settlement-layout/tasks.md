# Tasks

Run only the focused command named below. Never run a whole test suite for this change.
Do not add `covers_requirement` for the ADDED requirement (design D9).
Change only `tools/settlement_synthesis/generate.py`, `roles.py`, `workspace.py`, `__main__.py`, `tests/test_settlement_graph_generation.py` and the two documentation files of design D10.

## 1. Input

- [ ] 1.1 Confirm `single-cell-size-budget` is merged: `uv run --locked python -c "from tools.settlement_synthesis.budget import BUDGET_KINDS; from tools.settlement_synthesis.workspace import WorkspaceView; assert 'hamlet' in BUDGET_KINDS and hasattr(WorkspaceView, 'road_contacts')"` exits 0. If not, stop and report.
- [ ] 1.2 Add the `GenerationInput` field and the `analysis_input` change of design D2. Verify: `uv run --locked python -m unittest tests.test_settlement_graph_generation` passes unchanged.

## 2. Layout

- [ ] 2.1 Add `SINGLE_CELL_LABELS` to `roles.py`, the class rule of design D5 and `_generate_single_cell` per D3, D4, D6 and D7. Add the through-road, spur-end, junction, no-road, validity, determinism and beast-nation tests of D9. Verify: `uv run --locked python -m unittest tests.test_settlement_graph_generation` passes.
- [ ] 2.2 Add the "Single-cell layout" section and the two human-review questions of design D10 to `docs/development/settlement-synthesis.md`. Verify: `grep -c 'Single-cell layout' docs/development/settlement-synthesis.md` is at least 1.

## 3. Commands

- [ ] 3.1 Apply design D8 to `tools/settlement_synthesis/__main__.py`, with the batch tests of D9 and the remaining documentation edits of D10. Verify: `uv run --locked python -m unittest tests.test_settlement_graph_generation` passes, and `uv run --locked python -m tools.settlement_synthesis generate --help` lists `--kind`.

## 4. Gates

- [ ] 4.1 Run `uv run --locked python -m unittest tests.test_settlement_terrain_fit` and `uv run --locked python -m tools.settlement_synthesis lint`. Verify: both succeed with no edit to the lint or the budget.
- [ ] 4.2 Run `uv run --locked python -m tools.map_reference_context --check`, `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.contract_gate --change single-cell-settlement-layout` and `openspec validate single-cell-settlement-layout --strict`. Verify: all exit 0. The hand-off lists each new test with the delta requirement and scenario it establishes.

## Workflow follow-up

- During archive, after the delta sync, annotate the tests of the ADDED requirement with the identifier printed by `uv run --locked python -m tools.spec_traceability list`.
- A person reviews the two human-review questions added to `docs/development/settlement-synthesis.md` after the trial change places the first maps. It does not block archive.
