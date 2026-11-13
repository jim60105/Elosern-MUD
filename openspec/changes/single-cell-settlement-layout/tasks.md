# Tasks

Run only the two focused commands named below. Never run a whole test suite for this change.
Do not add `covers_requirement` for the ADDED requirements (design D9).
Change only files under `tools/settlement_synthesis/`, the two test modules and the two documentation files of design D10.

## 1. Budget

- [ ] 1.1 Confirm the two prerequisites are merged: `uv run --locked python -c "from elosern_map_core.schema import LOCATION_KINDS; from elosern_map_core.documents import WildernessEntryDeclaration as W; assert 'hamlet' in LOCATION_KINDS and 'single_cell_footprint' in W.__dataclass_fields__"` exits 0. If not, stop and report.
- [ ] 1.2 Apply design D1 to `tools/settlement_synthesis/budget.py`, with the budget tests of design D9 and the "Size budget" documentation edit of D10. Verify: `uv run --locked python -m unittest tests.test_settlement_terrain_fit` passes.

## 2. Layout

- [ ] 2.1 Add `road_contacts` to `WorkspaceView`, the `GenerationInput` field and the `analysis_input` change of design D2. Verify: `uv run --locked python -m unittest tests.test_settlement_graph_generation` passes unchanged.
- [ ] 2.2 Add `SINGLE_CELL_LABELS` to `roles.py`, the class rule of design D5 and `_generate_single_cell` per D3, D4 and D6. Add the through-road, spur-end, junction, no-road, validity, determinism and beast-nation tests of D9, and the "Single-cell layout" documentation section of D10. Verify: `uv run --locked python -m unittest tests.test_settlement_graph_generation` passes.

## 3. Lint and commands

- [ ] 3.1 Add the `road_contacts` parameter and `fit_entrance_mismatch` per design D7, pass it from the `lint` command and from `_generate_single_cell`, add the lint tests of D9 and the lint table row of D10. Verify: `uv run --locked python -m unittest tests.test_settlement_terrain_fit` passes.
- [ ] 3.2 Apply design D8 to `tools/settlement_synthesis/__main__.py`, with the batch tests of D9 and the remaining documentation edits of D10. Verify: `uv run --locked python -m unittest tests.test_settlement_graph_generation` passes, and `uv run --locked python -m tools.settlement_synthesis generate --help` lists `--kind`.

## 4. Gates

- [ ] 4.1 Run `uv run --locked python -m tools.settlement_synthesis lint`. Verify: it exits 0 on the shipped maps, as before this change.
- [ ] 4.2 Run `uv run --locked python -m tools.map_reference_context --check`, `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.contract_gate --change single-cell-settlement-layout` and `openspec validate single-cell-settlement-layout --strict`. Verify: all exit 0. The hand-off lists each new test with the delta requirement and scenario it establishes.

## Workflow follow-up

- During archive, after the delta sync, annotate the tests of the two ADDED requirements with the identifiers printed by `uv run --locked python -m tools.spec_traceability list`.
- A person reviews the two human-review questions added to `docs/development/settlement-synthesis.md` after the trial change places the first maps. It does not block archive.
