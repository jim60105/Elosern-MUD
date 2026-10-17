# Tasks

Total estimate: **6 hours**, including implementation, focused verification, documentation and integration.

## 1. Rule entry (1.5h)

- [ ] 1.1 Add `toggle_member_equipment` to `world/rules/party_inventory.py`; verify in `world/rules/tests/test_party_member_equipment.py` companion equip/replace/unequip, knocked-out admission, absent and forged members rejected with unchanged equipment, and no tick advance in exploration or in an active session.
- [ ] 1.2 Verify a saved companion draft entry is preflighted against the new equipment when the full draft submits (reuse the party-combat draft test helpers).

## 2. Action and client payload (2h)

- [ ] 2.1 Change `validate_inventory_toggle_equip_payload` to exactly `{actor_id, item_key}` and route the adapter through the rule; verify the exact-schema rejections and member-named messages in the service action tests.
- [ ] 2.2 Send the controlled figure's `actor_id` from `composables/intents.js` / `InventoryPanel.vue`; verify with the existing Vitest inventory panel and intents tests.

## 3. Text command and documentation (1.5h)

- [ ] 3.1 Extend `CmdToggleEquip` to `裝備 <物品> [= <成員>]` through `resolve_member_token`; verify text/action parity and refusals; document the syntax in both player command documents and run `tests/test_command_docs.py`.

## 4. Integration (1h)

- [ ] 4.1 Register the new test module in one shard, annotate canonical IDs for the modified `inventory-item-actions` requirements and the added `equipment-inventory` requirement, run the focused labels, the Node/Vitest files touched, the shard contract, `uv run --locked python -m tools.contract_gate` and `openspec validate party-member-equipment --strict`.
