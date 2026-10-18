# Tasks

Total estimate: **6 hours**, including implementation, focused verification, documentation and integration.

## 1. Transfer rule (3h)

- [x] 1.1 Implement `world/rules/party_inventory.py::transfer_item` with the ordered rejections, the fixed messages and the two-plan composition; verify in `world/rules/tests/test_party_inventory_transfer.py` success in both directions, knocked-out receiver admitted, every rejection code with a byte-identical attribute snapshot, and no tick/affinity change.
- [x] 1.2 Add snapshot/restore of both bags and contained objects with an injected failure after the giver write; verify both key lists, contained objects and caches equal their pre-transfer values; emit the `party_transfer` info event and assert it by patching the module binding.
  The event registers with `transaction.on_commit`, so the test asserts it through `captureOnCommitCallbacks(execute=True)` and a rolled-back transfer emits none. Both plans are computed inside the transfer savepoint, before the first write, so a plan-time quest-completion observer's deferred work is discarded on rollback (pinned by a completing-ACQUIRE test). The failure path also restores released room pin reasons and evicts created-mirror idmapper entries.

## 2. WebClient action (1.5h)

- [x] 2.1 Add `web/webclient/actions/party_actions.py` (`validate_party_transfer_payload`, `_party_transfer_adapter`) and register `party.transfer` with an empty affected-panel set; verify in `web/webclient/actions/tests/test_party_actions.py` the exact schema rejections, a forged receiver rejected without commander substitution, a success message and full-snapshot publication, and update the production registry composition test.

## 3. Integration (1.5h)

- [x] 3.1 Register both new test modules in exactly one shard each; run `uv run --locked python -m tools.observability_lint check`, the focused labels and `tests.test_evennia_test_optimization_contract`.
  `world.rules.tests.test_party_inventory_transfer` is registered in `rules-c`; `web.webclient.actions.tests.test_party_actions` is owned by the existing `web.webclient.actions` package label in `webclient-actions`. Focused runs: 33 transfer-rule cases, 6 action cases, 4 registry cases, 45 `test_party_scope` cases and 17 `test_inventory_actions` cases pass; the observability lint reports zero violations and the shard-ownership contract passes.
- [x] 3.2 Annotate with canonical IDs for the modified `webclient-action-dispatch` requirements and the added `party-item-transfer` requirements; run `uv run --locked python -m tools.contract_gate` and `openspec validate party-item-transfer --strict`.
  The two modified requirements are decorated with their canonical IDs (`action-identity-comes-only-from-the-authenticated-session`, `action-registries-are-allowlisted-and-duplicate-safe`). The added capability's intended IDs are recorded in both test-module docstrings; their `covers_requirement` decorators land with the archive/sync step, per the `party-member-authority` precedent, because traceability indexes only `openspec/specs/`. The contract gate reports 2280/2280 requirements covered and `openspec validate --strict` passes.
