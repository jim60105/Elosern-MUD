# Tasks

Total estimate: **6 hours**, including implementation, focused verification, documentation and integration.

## 1. Transfer rule (3h)

- [ ] 1.1 Implement `world/rules/party_inventory.py::transfer_item` with the ordered rejections, the fixed messages and the two-plan composition; verify in `world/rules/tests/test_party_inventory_transfer.py` success in both directions, knocked-out receiver admitted, every rejection code with a byte-identical attribute snapshot, and no tick/affinity change.
- [ ] 1.2 Add snapshot/restore of both bags and contained objects with an injected failure after the giver write; verify both key lists, contained objects and caches equal their pre-transfer values; emit the `party_transfer` info event and assert it by patching the module binding.

## 2. WebClient action (1.5h)

- [ ] 2.1 Add `web/webclient/actions/party_actions.py` (`validate_party_transfer_payload`, `_party_transfer_adapter`) and register `party.transfer` with an empty affected-panel set; verify in `web/webclient/actions/tests/test_party_actions.py` the exact schema rejections, a forged receiver rejected without commander substitution, a success message and full-snapshot publication, and update the production registry composition test.

## 3. Integration (1.5h)

- [ ] 3.1 Register both new test modules in exactly one shard each; run `uv run --locked python -m tools.observability_lint check`, the focused labels and `tests.test_evennia_test_optimization_contract`.
- [ ] 3.2 Annotate with canonical IDs for the modified `webclient-action-dispatch` requirements and the added `party-item-transfer` requirements; run `uv run --locked python -m tools.contract_gate` and `openspec validate party-item-transfer --strict`.
