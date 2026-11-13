# Tasks

Run only the focused commands named below. Never run a whole test suite for this change.
Do not add `covers_requirement` in any task here (design D9).

## 1. Exemption field

- [ ] 1.1 Confirm `village-hamlet-kinds` is merged: `uv run --locked python -c "from world.lore.anchors import AnchorKind; AnchorKind('hamlet')"` exits 0. If not, stop and report.
- [ ] 1.2 Add `spacing_exemption` to `_LOCATION` and `LocationDeclaration` per design D6, with the two scenarios of `specs/map-geographic-sources/spec.md` in `packages/map-core/tests/test_authoring.py`. Verify: from `packages/map-core`, `uv run --locked --extra generation python -m pytest tests/test_authoring.py -q` passes.

## 2. Pure check

- [ ] 2.1 Create `tools/settlement_spacing.py` with the dataclasses, constants and `check_spacing` rules of design D1, D2 and D5. Create `tests/test_settlement_spacing.py` with the scenarios of "Minimum spacing is checked by kind in straight-line distance", "An exemption mark skips minimum spacing" and "Villages and hamlets satisfy the placement identity rules". Register `tests.test_settlement_spacing` in shard `top-level-4` of `.github/top-level-shards.json`. Verify: `uv run --locked python -m unittest tests.test_settlement_spacing` and `uv run --locked python -m unittest tests.test_evennia_test_optimization_contract` pass.
- [ ] 2.2 Add the gap rule of design D3 and the area rule and `load_areas` of design D4, with the scenarios of "Road coverage bounds the gap between consecutive road settlements" and "Road coverage applies only inside completed areas". Create `tools/settlement_spacing_areas.json` with the content of design D4. Verify: `uv run --locked python -m unittest tests.test_settlement_spacing` passes.

## 3. Command and CI

- [ ] 3.1 Add `build_input` and `main` per design D7, with the scenario of "The spacing command reports by exit status and writes nothing". Verify: `uv run --locked python -m unittest tests.test_settlement_spacing` passes, and `uv run --locked python -m tools.settlement_spacing` prints `spacing: 0 problems` and exits 0 on the shipped data.
- [ ] 3.2 Add the workflow step and the contract test of design D8. Verify: `uv run --locked python -m unittest tests.test_quality_gate_contract` passes.
- [ ] 3.3 Apply the documentation edits of design D10. Verify: the command line in `verification.md` runs as written and exits 0.

## 4. Gates

- [ ] 4.1 After the last source edit, run `uv run --locked python -m tools.map_reference_context`. Verify: the same command with `--check` exits 0.
- [ ] 4.2 Run `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.contract_gate --change settlement-spacing-validation` and `openspec validate settlement-spacing-validation --strict`. Verify: all exit 0. The hand-off lists each new test with the delta requirement and scenario it establishes.

## Workflow follow-up

- During archive, after the delta sync, annotate the tests with the identifiers printed by `uv run --locked python -m tools.spec_traceability list`.
