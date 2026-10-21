# Tasks

## 1. Owning implementation and evidence

- [x] 1.1 Use branch `feat/implement-sparse-settlement-graphs` and worktree `.worktrees/implement-sparse-settlement-graphs` as luna after all Batch dependencies resolve; verify prerequisite contract/API availability, including the later companion owner where required.
- [x] 1.2 Implement Add sparse node/road synchronization and stable in-place coordinate identity binding without activating meter coordinates. Edit world/maps/bootstrap.py::sync_grid, world/maps/map_data.py::XYMAP_DATA_LIST, typeclasses/rooms.py::GridRoom; sparse graph route adapter replacing dense allocation. Verify all delta scenarios with focused behavior tests in the existing owning test suites; use small synthetic fixtures for mechanics and registered shipped-data contract tests for exact authored tables.
- [x] 1.3 Update the affected developer documentation/changelog following the existing repository convention with the unit/ownership contract and actual cutover behavior; verify documented declarations and runtime APIs match the scenario tests.
- [x] 1.4 Attach substantive scenario assertions with literal `covers_requirement` IDs, including `grid-room-sync::sparse-authored-graphs-synchronize-without-identity-loss`, `grid-room-sync::sync-grid-is-distinct-from-sync-all-and-instantiates-real-rooms-and-exits`. Verify each modified requirement retains meaningful evidence for all retained scenarios, then run `uv run --locked python -m tools.spec_traceability check`.

- [x] 1.5 Converge `world/maps/bootstrap.py::sync_grid` under this change’s unit/identity contract; verify its owning scenario regression tests and update the corresponding developer reference when its contract changes.
- [x] 1.6 Converge `world/maps/map_data.py::XYMAP_DATA_LIST` under this change’s unit/identity contract; verify its owning scenario regression tests and update the corresponding developer reference when its contract changes.
- [x] 1.7 Converge `typeclasses/rooms.py::GridRoom; sparse graph route adapter replacing dense allocation` under this change’s unit/identity contract; verify its owning scenario regression tests and update the corresponding developer reference when its contract changes.

## 2. Consumer integration and handoff

- [x] 2.0 Extend world/maps/tests/test_bootstrap.py and sparse shortest-path tests with substantive assertions for this change’s scenarios; verify the focused suite passes and its documentation/fixture registrations match the new contract.

- [x] 2.1 Exercise actual synchronization/movement/rendering consumers affected by this change; verify no old-unit hop/rank/dense-lattice assumptions remain in its owned paths and no compatibility aliases, temporary scaffolds or duplicate authority remain.
- [x] 2.2 Register every new or moved non-browser test module in `.github/evennia-shards.json`; register new browser classes/methods in `.github/browser-shards.json`. Use the synthetic test-data kit or file-local fixtures except registered data-contract tests; verify `uv run --locked python -m tools.test_data_lint check`.
- [x] 2.3 Keep production logging through `world.observability`, with `tools/observability_freeze.json` shrink-only; verify `uv run --locked python -m tools.observability_lint check`.
- [x] 2.4 Update `docs/game/commands.md` and `docs/game/command-reference.md` if movement behavior or command surfaces change; verify `tests/test_command_docs.py` for relevant syntax/context changes, without inventing transport or route commands.
- [x] 2.5 Run focused owning tests and `uv run --locked python -m tools.contract_gate` before handoff/archive; report exercised evidence and `openspec validate implement-sparse-settlement-graphs --strict`, with no unchecked main-spec traceability omissions.
