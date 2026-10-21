# Tasks

Worker: luna
Branch: `feat/establish-mental-reserve-core`
Worktree: `.worktrees/establish-mental-reserve-core`

## 1. Exact policy and construction

- [ ] 1.1 Add the proposed policy/state API in `world/rules/fatigue.py` and one validated read-only rulebook source; add proposed `world/rules/tests/test_fatigue.py` synthetic behavior tests proving all boundary units, exact rates, split equivalence, saturation and 6000-second wake. Verify independently known numeric results rather than a copied registry table.
- [ ] 1.2 Wire explicit baseline initialization into `typeclasses/entities.py::LivingEntity.at_object_creation` and its authored construction/synchronization owners without refilling valid fatigue or repairing corrupt input. Verify new construction, repeat synchronization, malformed state and database reload tests; document reserve independence and units in the module contract.
- [ ] 1.3 Implement immutable interval/boundary prediction, completion policies and rational threshold offsets. Verify pure repeated reads, fractional-unit thresholds, 25987.5-metre calibration and identical accepted integer-second prediction/settlement in the new synthetic test module; document the exact traversal API in its public docstrings.

- [ ] 1.4 Annotate this group's substantive behavior tests with `covers_requirement` and literal derived requirement IDs for every owning new/modified requirement. Register every new/moved non-browser test module in `.github/evennia-shards.json` and every new browser class/method in `.github/browser-shards.json`; use `world/tests/synthetic_data.py` or file-local synthetic fixtures, with shipped-content names restricted to registered data-contract tests. Verify traceability and manifest registration for the group.

## 2. Atomic writer contract

- [ ] 2.1 Implement `settle_fatigue_intervals` with all-member validation, stale-start rejection and declared reserve/posture snapshot surfaces for enclosing owners. Verify a second-member write fault restores every member and cached attribute with no success event.
- [ ] 2.2 Emit actual committed state transitions through `world.observability` with available member/commander/room/tick/session/reason context. Verify rolled-back writes emit no transition success and pure predictions emit no events.

- [ ] 2.3 Annotate this group's substantive behavior tests with `covers_requirement` and literal derived requirement IDs for every owning new/modified requirement. Register every new/moved non-browser test module in `.github/evennia-shards.json` and every new browser class/method in `.github/browser-shards.json`; use `world/tests/synthetic_data.py` or file-local synthetic fixtures, with shipped-content names restricted to registered data-contract tests. Verify traceability and manifest registration for the group.

## 3. Integrated handoff gates

- [ ] 3.1 Run the owning focused suites and `uv run --locked python -m tools.contract_gate` before handoff/archive; retain actual command output as implementation evidence, without claiming planning artifacts prove runtime behavior.
- [ ] 3.2 Run `uv run --locked python -m tools.spec_traceability check`, `uv run --locked python -m tools.test_data_lint check`, and `uv run --locked python -m tools.observability_lint check`; verify substantive literal-ID coverage and keep `tools/observability_freeze.json` shrink-only. Use only `world.observability` for production logging.
- [ ] 3.3 Run `tests/test_command_docs.py` through the repository's documented test runner for every changed command surface, then `openspec validate establish-mental-reserve-core --strict`; verify docs, deltas and real test evidence agree before handoff.
