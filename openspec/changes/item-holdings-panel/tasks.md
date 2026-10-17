# Tasks

Total estimate: **6.5 hours**, including implementation, focused verification, documentation and integration.

## 1. Rules reads (2.5h)

- [ ] 1.1 Add the injected-equipment parameter to the breakdown read model and `equipment_delta`/`item_holdings`; verify in `world/rules/tests/test_item_holdings.py` the independent sword cases (+6, −4), accessory append, full accessory slots refusal, non-equipment null delta, an already-equipped row, combat receive refusal, absent receiver refusal, and a write-free attribute snapshot; prove the default read-model path is unchanged.

## 2. Panel and selection (2.5h)

- [ ] 2.1 Extend `party.view_member` to `{member_id, tab, skill_key, item_key}` and the stored selection; implement and register `item_holdings` v1; verify action schema tests, presenter tests (no selection, commander-first rows, possession-identical), maximal bound, and the JS mirror/parity/allowlist contract.

## 3. Integration (1.5h)

- [ ] 3.1 Add `item_holdings` to the affected panels, register new test modules in one shard each, annotate canonical IDs for the added `webclient-item-holdings-panel` requirements and the modified `webclient-party-panel` requirement, run `uv run --locked python -m tools.contract_gate` and `openspec validate item-holdings-panel --strict`.
