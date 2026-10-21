# Tasks

## 1. Owning implementation and evidence

- [ ] 1.1 Use branch `feat/integrate-fatigue-aware-traversal` and worktree `.worktrees/integrate-fatigue-aware-traversal` as luna after all Batch dependencies resolve; verify prerequisite contract/API availability, including the later companion owner where required.
- [ ] 1.2 Implement Consume the external fatigue/sleep contract for piecewise traversal prediction, pre-node depletion refusal and atomic physiology settlement. Edit world/rules/movement.py::charge_movement, world/rules/party.py::follow_scope, typeclasses/exits.py traversal preflight, world/rules/movement_settlement.py::_snapshot_movement_state/_compensate, world/rules/clock.py::build_advance_snapshot_registry. Verify all delta scenarios with focused behavior tests in the existing owning test suites; use small synthetic fixtures for mechanics and registered shipped-data contract tests for exact authored tables.
- [ ] 1.3 Update the affected developer documentation/changelog following the existing repository convention with the unit/ownership contract and actual cutover behavior; verify documented declarations and runtime APIs match the scenario tests.
- [ ] 1.4 Attach substantive scenario assertions with literal `covers_requirement` IDs, including `movement-cost-charging::traversal-integrates-fatigue-over-remaining-distance`, `movement-cost-charging::sparse-edge-admission-refuses-pre-destination-depletion`, `movement-settlement-atomicity::fatigue-aware-movement-restores-all-owning-surfaces`. Verify each modified requirement retains meaningful evidence for all retained scenarios, then run `uv run --locked python -m tools.spec_traceability check`.

- [ ] 1.5 Converge `world/rules/movement.py::charge_movement` under this change’s unit/identity contract; verify its owning scenario regression tests and update the corresponding developer reference when its contract changes.
- [ ] 1.6 Converge `world/rules/party.py::follow_scope` under this change’s unit/identity contract; verify its owning scenario regression tests and update the corresponding developer reference when its contract changes.
- [ ] 1.7 Converge `typeclasses/exits.py traversal preflight` under this change’s unit/identity contract; verify its owning scenario regression tests and update the corresponding developer reference when its contract changes.
- [ ] 1.8 Converge `world/rules/movement_settlement.py::_snapshot_movement_state/_compensate` under this change’s unit/identity contract; verify its owning scenario regression tests and update the corresponding developer reference when its contract changes.
- [ ] 1.9 Converge `world/rules/clock.py::build_advance_snapshot_registry` under this change’s unit/identity contract; verify its owning scenario regression tests and update the corresponding developer reference when its contract changes.

## 2. Consumer integration and handoff

- [ ] 2.0 Extend world/rules/tests/test_party_follow_possession.py and world/rules/tests/test_movement_settlement.py with substantive assertions for this change’s scenarios; verify the focused suite passes and its documentation/fixture registrations match the new contract.

- [ ] 2.1 Exercise actual synchronization/movement/rendering consumers affected by this change; verify no old-unit hop/rank/dense-lattice assumptions remain in its owned paths and no compatibility aliases, temporary scaffolds or duplicate authority remain.
- [ ] 2.2 Register every new or moved non-browser test module in `.github/evennia-shards.json`; register new browser classes/methods in `.github/browser-shards.json`. Use the synthetic test-data kit or file-local fixtures except registered data-contract tests; verify `uv run --locked python -m tools.test_data_lint check`.
- [ ] 2.3 Keep production logging through `world.observability`, with `tools/observability_freeze.json` shrink-only; verify `uv run --locked python -m tools.observability_lint check`.
- [ ] 2.4 Update `docs/game/commands.md` and `docs/game/command-reference.md` if movement behavior or command surfaces change; verify `tests/test_command_docs.py` for relevant syntax/context changes, without inventing transport or route commands.
- [ ] 2.5 Run focused owning tests and `uv run --locked python -m tools.contract_gate` before handoff/archive; report exercised evidence and `openspec validate integrate-fatigue-aware-traversal --strict`, with no unchecked main-spec traceability omissions.
