# Tasks

Run only the focused commands named below. Never run a whole test suite for this change.

## 1. Removal

- [ ] 1.1 Confirm `valhalla-village-placement` is merged: `grep -c 'northwest_highland_forest' tools/settlement_spacing_areas.json` prints 1 and `uv run --locked python -m tools.settlement_spacing` prints `spacing: 0 problems`. If not, stop and report.
- [ ] 1.2 Apply design D1 and D2. Verify: `uv run --locked python -m unittest tests.test_settlement_spacing` passes, `test -e tools/settlement_spacing_areas.json` fails, `grep -rn "settlement_spacing_areas\|load_areas\|--areas" tools tests .github .agents docs/development` prints nothing, and `uv run --locked python -m tools.settlement_spacing --areas x` exits 2 with an argument error.
- [ ] 1.3 Apply the documentation edit of design D4. Verify: `grep -ci 'completed area' .agents/skills/map-data-authoring/references/locations-and-districts.md` prints 0.

## 2. Boundary gaps

- [ ] 2.1 Run `uv run --locked python -m tools.settlement_spacing`. If it prints `spacing: 0 problems`, record that in the hand-off and skip to group 3. Otherwise close each reported `road_gap` per design D3. Verify: the command prints `spacing: 0 problems`, `uv run --locked python -m tools.settlement_synthesis lint` exits 0, `uv run --locked python -m tools.road_network --check` exits 0, and the hand-off lists every hamlet added with its gap.

## 3. Gates

- [ ] 3.1 Run `uv run --locked python -m unittest tests.test_quality_gate_contract`. Verify: it passes; the workflow step runs the command with no option and needs no edit.
- [ ] 3.2 Run `uv run --locked python -m tools.map_reference_context --check`, `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.contract_gate --change road-coverage-area-removal` and `openspec validate road-coverage-area-removal --strict`. Verify: all exit 0. If task 2.1 added a hamlet, regenerate the reference context first and run the settlement-sensitive modules of `docs/development/settlement-synthesis.md`, one per command.
