# Tasks

Total estimate: **5.5 hours**, including implementation, focused verification, documentation and integration.

## 1. Rule entry (1.5h)

- [ ] 1.1 Add `use_member_item`; verify in `world/rules/tests/test_companion_field_item_use.py` a companion mana potion (MP 40 → 70 of 120, her count −1, commander bag unchanged, one six-second advance settling the present party), SELF binding, and knocked-out/absent/forged rejections with nothing consumed.

## 2. Action and client payload (1.5h)

- [ ] 2.1 Make `inventory.use` exactly `{actor_id, item_key[, target_key]}` and route the adapter through the rule with member-relative target resolution; keep the in-session rejection; verify service action schema/adapter tests and the Vitest intents payload for the controlled figure.

## 3. Text command and documentation (1.5h)

- [ ] 3.1 Extend `CmdUseItem` with `= <成員>` (field use outside combat, actor item command inside a session); verify text/action parity and draft-entry parity; document the syntax in both player command documents and run `tests/test_command_docs.py`.

## 4. Integration (1h)

- [ ] 4.1 Register the new module in one shard, annotate canonical IDs for the modified `inventory-item-actions` requirements and the added `companion-field-actions` requirements, run the focused labels, the shard contract, `uv run --locked python -m tools.contract_gate` and `openspec validate companion-field-item-use --strict`.
